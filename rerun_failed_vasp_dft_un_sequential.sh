#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/mnt/disk002/CaoJie_Workspace/CrystalDiT"
DFT_DIR="${ROOT_DIR}/chgnet_results_CrystalDiT/dft_un"
LOG_DIR="${ROOT_DIR}/chgnet_results_CrystalDiT/vasp_batch_logs"
FAILED_FILE="${LOG_DIR}/failed_jobs.txt"
RERUN_LOG_DIR="${LOG_DIR}/rerun_np4"

NP_PER_JOB=4
MPIRUN_BIN="${MPIRUN_BIN:-mpirun}"
VASP_BIN="${VASP_BIN:-vasp_std}"
VASP_CMD="${MPIRUN_BIN} -np ${NP_PER_JOB} ${VASP_BIN}"

SUMMARY_FILE="${RERUN_LOG_DIR}/summary.csv"
STILL_FAILED_FILE="${RERUN_LOG_DIR}/still_failed_jobs.txt"
COMPLETED_FILE="${RERUN_LOG_DIR}/completed_jobs.txt"
SKIPPED_FILE="${RERUN_LOG_DIR}/skipped_jobs.txt"

mkdir -p "${RERUN_LOG_DIR}"
echo "folder,status,duration_seconds" > "${SUMMARY_FILE}"
: > "${STILL_FAILED_FILE}"
: > "${COMPLETED_FILE}"
: > "${SKIPPED_FILE}"

echo "DFT input root: ${DFT_DIR}"
echo "Failed jobs file: ${FAILED_FILE}"
echo "Rerun command: ${VASP_CMD}"
echo "Rerun mode: sequential"
echo "Rerun log dir: ${RERUN_LOG_DIR}"
echo

if [ ! -d "${DFT_DIR}" ]; then
    echo "ERROR: DFT directory does not exist: ${DFT_DIR}"
    exit 1
fi

if [ ! -f "${FAILED_FILE}" ]; then
    echo "ERROR: Failed jobs file does not exist: ${FAILED_FILE}"
    echo "Run run_vasp_dft_un_parallel.sh first, or create this file manually with one failed directory per line."
    exit 1
fi

if ! command -v "${MPIRUN_BIN}" >/dev/null 2>&1; then
    echo "ERROR: MPI launcher not found: ${MPIRUN_BIN}"
    echo "Please load your MPI/VASP environment first, or run with MPIRUN_BIN=/full/path/to/mpirun."
    exit 1
fi

if ! command -v "${VASP_BIN}" >/dev/null 2>&1; then
    echo "ERROR: VASP executable not found: ${VASP_BIN}"
    echo "Please load your VASP environment first, or run with VASP_BIN=/full/path/to/vasp_std."
    exit 1
fi

is_completed() {
    local calc_dir="$1"
    [ -f "${calc_dir}/OUTCAR" ] && grep -q "Voluntary context switches" "${calc_dir}/OUTCAR" 2>/dev/null
}

backup_old_outputs() {
    local calc_dir="$1"
    local backup_dir="$2"

    mkdir -p "${backup_dir}"

    for file in stdout.log stderr.log vasp_run.info OUTCAR OSZICAR CONTCAR XDATCAR vasprun.xml; do
        if [ -e "${calc_dir}/${file}" ]; then
            mv "${calc_dir}/${file}" "${backup_dir}/${file}"
        fi
    done
}

run_one_failed_job() {
    local calc_dir="$1"
    local calc_name
    calc_name="$(basename "${calc_dir}")"

    echo "============================================================"
    echo "[$(date)] RERUN START ${calc_name}"
    echo "Directory: ${calc_dir}"
    echo "============================================================"

    if [ ! -d "${calc_dir}" ]; then
        echo "[$(date)] FAIL ${calc_name}: directory does not exist"
        echo "${calc_name},MISSING_DIR,0" >> "${SUMMARY_FILE}"
        echo "${calc_dir}" >> "${STILL_FAILED_FILE}"
        return 0
    fi

    if is_completed "${calc_dir}"; then
        echo "[$(date)] SKIP ${calc_name}: completed OUTCAR found"
        echo "${calc_name},SKIPPED_COMPLETED,0" >> "${SUMMARY_FILE}"
        echo "${calc_dir}" >> "${SKIPPED_FILE}"
        return 0
    fi

    for required_file in INCAR POSCAR POTCAR KPOINTS; do
        if [ ! -f "${calc_dir}/${required_file}" ]; then
            echo "[$(date)] FAIL ${calc_name}: missing ${required_file}"
            echo "${calc_name},MISSING_${required_file},0" >> "${SUMMARY_FILE}"
            echo "${calc_dir}" >> "${STILL_FAILED_FILE}"
            return 0
        fi
    done

    local timestamp
    timestamp="$(date +%Y%m%d_%H%M%S)"
    local backup_dir="${calc_dir}/failed_run_backup_${timestamp}"
    backup_old_outputs "${calc_dir}" "${backup_dir}"
    echo "Backed up previous outputs to: ${backup_dir}"

    local start_time
    local end_time
    local duration
    local exit_code
    start_time=$(date +%s)

    set +e
    (
        cd "${calc_dir}" || exit 99
        echo "Start time: $(date)" > vasp_run.info
        echo "Command: ${VASP_CMD}" >> vasp_run.info
        echo "Previous failed outputs backup: ${backup_dir}" >> vasp_run.info
        ${VASP_CMD} > stdout.log 2> stderr.log
        exit_code=$?
        echo "End time: $(date)" >> vasp_run.info
        echo "Exit code: ${exit_code}" >> vasp_run.info
        exit "${exit_code}"
    )
    exit_code=$?
    set -e

    end_time=$(date +%s)
    duration=$((end_time - start_time))

    if [ "${exit_code}" -eq 0 ] && is_completed "${calc_dir}"; then
        echo "[$(date)] RERUN DONE ${calc_name}: ${duration} s"
        echo "${calc_name},SUCCESS,${duration}" >> "${SUMMARY_FILE}"
        echo "${calc_dir}" >> "${COMPLETED_FILE}"
    elif [ "${exit_code}" -eq 0 ]; then
        echo "[$(date)] RERUN WARNING ${calc_name}: exit code 0 but OUTCAR completion marker not found, ${duration} s"
        echo "${calc_name},NO_COMPLETION_MARKER,${duration}" >> "${SUMMARY_FILE}"
        echo "${calc_dir}" >> "${STILL_FAILED_FILE}"
    else
        echo "[$(date)] RERUN FAIL ${calc_name}: exit code ${exit_code}, ${duration} s"
        echo "${calc_name},FAILED_EXIT_${exit_code},${duration}" >> "${SUMMARY_FILE}"
        echo "${calc_dir}" >> "${STILL_FAILED_FILE}"
    fi

    echo
    return 0
}

mapfile -t FAILED_DIRS < <(grep -E '^/' "${FAILED_FILE}" | sort -u)
TOTAL=${#FAILED_DIRS[@]}

echo "Found ${TOTAL} unique failed calculation folders."
echo

if [ "${TOTAL}" -eq 0 ]; then
    echo "No failed folders found in ${FAILED_FILE}."
    exit 0
fi

for idx in "${!FAILED_DIRS[@]}"; do
    echo "Progress: $((idx + 1))/${TOTAL}"
    run_one_failed_job "${FAILED_DIRS[$idx]}"
done

SUCCESS_COUNT=$(grep -c ',SUCCESS,' "${SUMMARY_FILE}" || true)
SKIP_COUNT=$(grep -c ',SKIPPED_COMPLETED,' "${SUMMARY_FILE}" || true)
FAIL_COUNT=$(wc -l < "${STILL_FAILED_FILE}")

echo "============================================================"
echo "Rerun finished."
echo "Total failed folders considered: ${TOTAL}"
echo "Rerun success: ${SUCCESS_COUNT}"
echo "Skipped completed: ${SKIP_COUNT}"
echo "Still failed/missing/no marker: ${FAIL_COUNT}"
echo "Summary: ${SUMMARY_FILE}"
echo "Completed jobs: ${COMPLETED_FILE}"
echo "Still failed jobs: ${STILL_FAILED_FILE}"
echo "Skipped jobs: ${SKIPPED_FILE}"
echo "============================================================"
