#!/usr/bin/env bash
set -euo pipefail

# Large structures crash at DAV:5 (first charge mixing) with SIGSEGV in
# hamiltmu_/racc0mu_ because per-process stack defaults to 8 MB.
# Raise it before xargs/mpirun so all child vasp_std ranks inherit it.
# ulimit -s unlimited || echo "WARNING: failed to raise stack limit; large structures may crash"


BATCH_START_TIME=$(date +%s)
BATCH_START_DISPLAY=$(date '+%Y-%m-%d %H:%M:%S')

ROOT_DIR="/mnt/disk002/CaoJie_Workspace/CrystalDiT/chgnet_results_CrystalDiT_mpts52_ep38000_seed123"
DFT_DIR="${ROOT_DIR}/dft_un"

NP_PER_JOB=10
MAX_PARALLEL_JOBS=4

MPIRUN_BIN="${MPIRUN_BIN:-mpirun}"
VASP_BIN="${VASP_BIN:-vasp_std}"
VASP_CMD="${MPIRUN_BIN} -np ${NP_PER_JOB} ${VASP_BIN}"

LOG_DIR="${ROOT_DIR}/vasp_batch_logs"
mkdir -p "${LOG_DIR}"

SUMMARY_FILE="${LOG_DIR}/summary.csv"
FAILED_FILE="${LOG_DIR}/failed_jobs.txt"

echo "folder,status,duration_seconds" > "${SUMMARY_FILE}"
: > "${FAILED_FILE}"

echo "DFT input root: ${DFT_DIR}"
echo "VASP command per job: ${VASP_CMD}"
echo "Max parallel jobs: ${MAX_PARALLEL_JOBS}"
echo "Total MPI ranks if fully occupied: $((NP_PER_JOB * MAX_PARALLEL_JOBS))"
echo "Batch log dir: ${LOG_DIR}"
echo

if [ ! -d "${DFT_DIR}" ]; then
    echo "ERROR: DFT directory does not exist: ${DFT_DIR}"
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

run_one_job() {
    local calc_dir="$1"
    local calc_name
    calc_name="$(basename "${calc_dir}")"

    echo "[$(date)] START ${calc_name}"

    if [ -f "${calc_dir}/OUTCAR" ] && grep -q "Voluntary context switches" "${calc_dir}/OUTCAR" 2>/dev/null; then
        echo "[$(date)] SKIP ${calc_name}: completed OUTCAR found"
        echo "${calc_name},SKIPPED,0" >> "${SUMMARY_FILE}"
        return 0
    fi

    for required_file in INCAR POSCAR POTCAR KPOINTS; do
        if [ ! -f "${calc_dir}/${required_file}" ]; then
            echo "[$(date)] FAIL ${calc_name}: missing ${required_file}"
            echo "${calc_name},MISSING_${required_file},0" >> "${SUMMARY_FILE}"
            echo "${calc_dir}" >> "${FAILED_FILE}"
            return 0
        fi
    done

    local start_time
    local end_time
    local duration
    start_time=$(date +%s)

    local exit_code
    (
        set +e
        cd "${calc_dir}" || exit 99
        echo "Start time: $(date)" > vasp_run.info
        echo "Command: ${VASP_CMD}" >> vasp_run.info
        ${VASP_CMD} > stdout.log 2> stderr.log
        exit_code=$?
        echo "End time: $(date)" >> vasp_run.info
        echo "Exit code: ${exit_code}" >> vasp_run.info
        exit "${exit_code}"
    )
    exit_code=$?
    end_time=$(date +%s)
    duration=$((end_time - start_time))

    if [ "${exit_code}" -eq 0 ]; then
        echo "[$(date)] DONE ${calc_name}: ${duration} s"
        echo "${calc_name},SUCCESS,${duration}" >> "${SUMMARY_FILE}"
    else
        echo "[$(date)] FAIL ${calc_name}: exit code ${exit_code}, ${duration} s"
        echo "${calc_name},FAILED_EXIT_${exit_code},${duration}" >> "${SUMMARY_FILE}"
        echo "${calc_dir}" >> "${FAILED_FILE}"
        return 0
    fi
}

export -f run_one_job
export VASP_CMD SUMMARY_FILE FAILED_FILE

mapfile -t CALC_DIRS < <(find "${DFT_DIR}" -mindepth 1 -maxdepth 1 -type d | sort)

# Optional resume point: only process folders whose name is >= START_FROM
# (folder names are zero-padded, so lexicographic order == numeric order).
# Example: START_FROM=008630 bash run_vasp_dft_un_parallel.sh
if [ -n "${START_FROM:-}" ]; then
    mapfile -t CALC_DIRS < <(printf '%s\n' "${CALC_DIRS[@]}" | awk -v s="${DFT_DIR}/${START_FROM}" '$0 >= s')
fi

TOTAL=${#CALC_DIRS[@]}
echo "Found ${TOTAL} calculation folders."
echo

if [ "${TOTAL}" -eq 0 ]; then
    echo "ERROR: No calculation folders found."
    exit 1
fi

printf "%s\n" "${CALC_DIRS[@]}" | xargs -I {} -P "${MAX_PARALLEL_JOBS}" bash -c 'run_one_job "$@"' _ {}

BATCH_END_TIME=$(date +%s)
BATCH_END_DISPLAY=$(date '+%Y-%m-%d %H:%M:%S')
BATCH_DURATION=$((BATCH_END_TIME - BATCH_START_TIME))

read -r ATTEMPTED_COUNT ATTEMPTED_SECONDS SUCCESS_COUNT SUCCESS_SECONDS < <(
    awk -F, 'NR > 1 {
        if ($2 == "SUCCESS") {
            success_count++
            success_total += $3
            attempted_count++
            attempted_total += $3
        } else if ($2 ~ /^FAILED_EXIT_/) {
            attempted_count++
            attempted_total += $3
        }
    } END {
        printf "%d %d %d %d\n", attempted_count, attempted_total, success_count, success_total
    }' "${SUMMARY_FILE}"
)

if [ "${SUCCESS_COUNT}" -gt 0 ]; then
    AVG_SUCCESS_SECONDS=$(awk -v total="${SUCCESS_SECONDS}" -v count="${SUCCESS_COUNT}" \
        'BEGIN { printf "%.2f", total / count }')
else
    AVG_SUCCESS_SECONDS="N/A"
fi

if [ "${ATTEMPTED_COUNT}" -gt 0 ]; then
    AVG_ATTEMPTED_SECONDS=$(awk -v total="${ATTEMPTED_SECONDS}" -v count="${ATTEMPTED_COUNT}" \
        'BEGIN { printf "%.2f", total / count }')
else
    AVG_ATTEMPTED_SECONDS="N/A"
fi

printf -v BATCH_DURATION_FORMATTED '%02d:%02d:%02d' \
    $((BATCH_DURATION / 3600)) $(((BATCH_DURATION % 3600) / 60)) $((BATCH_DURATION % 60))

echo
echo "============================================================"
echo "Batch finished."
echo "Start time: ${BATCH_START_DISPLAY}"
echo "End time: ${BATCH_END_DISPLAY}"
echo "Complete runtime: ${BATCH_DURATION} s (${BATCH_DURATION_FORMATTED})"
echo "Structures attempted: ${ATTEMPTED_COUNT}"
echo "Structures completed successfully: ${SUCCESS_COUNT}"
echo "Average time per successful structure: ${AVG_SUCCESS_SECONDS} s"
echo "Average time per attempted structure: ${AVG_ATTEMPTED_SECONDS} s"
echo "Summary file: ${SUMMARY_FILE}"
echo "Failed jobs file: ${FAILED_FILE}"
echo "============================================================"