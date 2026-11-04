import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent  # 获取当前 Python 文件的路径，把路径解析成绝对路径，然后获取其父目录
os.chdir(ROOT)  # 切换当前工作目录到 ROOT

# 设置环境变量
os.environ["CUDA_VISIBLE_DEVICES"] = "0, 1, 2, 3"  # 0, 1, 2, 3


train_cmds = [
    # [
    #     "python",
    #     "train_crystal_dit.py",
    #     "--data_dir", "./datasets/mp_20",
    #     "--max_atoms", "20",
    #     "--hidden_size", "512",
    #     "--depth", "18",
    #     "--num_heads", "8",
    #     "--diffusion_steps", "1000",
    #     "--batch_size", "512",
    #     "--epochs", "50000",
    #     "--save_every", "250",
    #     "--output_dir", "./output/crystal_dit",
    #     # "--resume", "./output/crystal_dit/latest_checkpoint.pt",
    #     "--seed", "42",
    # ],
    [
        "python",
        "train_crystal_dit.py",
        "--data_dir", "datasets/mpts_52",
        "--max_atoms", "52",
        "--hidden_size", "512",
        "--depth", "18",
        "--num_heads", "8",
        "--diffusion_steps", "1000",
        "--batch_size", "256",
        "--epochs", "50000",
        "--save_every", "250",
        "--output_dir", "output/crystaldit_mpts52",
        # "--resume", "./output/crystal_dit/latest_checkpoint.pt",
        "--seed", "42",
    ],
]

""" training 
for i, cmd in enumerate(train_cmds, start=1):
    print("--------------------------------------------------")
    print(f"Running command {i}/{len(train_cmds)}")
    print(" ".join(cmd))
    print("--------------------------------------------------")
    
    try:
        subprocess.run(cmd, check=True)
        print(f"Command {i} finished successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Command {i} failed with return code {e.returncode}.")
        print("Continue to next command...")
    print("--------------------------------------------------")
"""

sample_cmds = [
    # [
    #     "python",
    #     "generate_crystals.py",
    #     "--checkpoint", "./checkpoints/best_model.pt",
    #     "--max_atoms", "20",
    #     "--hidden_size", "512",
    #     "--depth", "18",
    #     "--num_heads", "8",
    #     "--diffusion_steps", "1000",
    #     "--num_samples", "10000",
    #     "--batch_size", "64",
    #     "--output_dir", "generate_crystals/CrystalDiT_crystals",
    #     "--device", "cuda",
    #     "--use_multi_gpu"
    # ],
    [
        "python",
        "generate_crystals.py",
        "--checkpoint", "output/crystaldit_mpts52/checkpoint_epoch_38000.pt",
        "--max_atoms", "52",
        "--hidden_size", "512",
        "--depth", "18",
        "--num_heads", "8",
        "--diffusion_steps", "1000",
        "--num_samples", "10000",
        "--batch_size", "64",
        "--output_dir", "crystaldit_mpts52_crystals_ma52/checkpoint_epoch_38000_generated",
        "--device", "cuda",
        "--use_multi_gpu"
    ],
]
""" sample 
for i, cmd in enumerate(sample_cmds, start=1):
    print("--------------------------------------------------")
    print(f"Running command {i}/{len(sample_cmds)}")
    print(" ".join(cmd))
    print("--------------------------------------------------")
    
    try:
        subprocess.run(cmd, check=True)
        print(f"Command {i} finished successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Command {i} failed with return code {e.returncode}.")
        print("Continue to next command...")
    print("--------------------------------------------------")
"""

eval_01_cmds = [
    # [
    #     "python", 
    #     "eval_script/batch_eval_metrics.py",
    #     "Generate_crystals",
    #     "--csv_folder", "datasets/mp_20"
    # ],
    [
        "python", 
        "eval_script/batch_eval_metrics.py",
        "generate_crystals",
        "--csv_folder", "datasets/mpts_52"
    ],
]
"""  
for i, cmd in enumerate(eval_01_cmds, start=1):
    print("--------------------------------------------------")
    print(f"Running command {i}/{len(eval_01_cmds)}")
    print(" ".join(cmd))
    print("--------------------------------------------------")
    
    try:
        subprocess.run(cmd, check=True)
        print(f"Command {i} finished successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Command {i} failed with return code {e.returncode}.")
        print("Continue to next command...")
    print("--------------------------------------------------")
"""

chgnet_cmds = [
    # [
    #     "python", 
    #     "eval_script/chgnet_process.py",
    #     "--cif_folder", "Generate_crystals/mattergen_crystals",
    #     "--csv_file", "Generate_crystals_flowmm_aligned_analysis/mattergen_crystals_results.csv",
    #     "--mp_hull_path", "datasets/mp_hull/2024-08-07-ppd-mp.pkl",
    #     "--sample_size", "500",
    #     "--max_steps", "2500",
    #     "--dft_threshold", "0.5",
    #     "--output_dir", "chgnet_results_mattergen",
    #     "--un_only"
    # ],
    # [
    #     "python", 
    #     "eval_script/chgnet_process.py",
    #     "--cif_folder", "Generate_crystals/diffcsp-pp_crystals",
    #     "--csv_file", "Generate_crystals_flowmm_aligned_analysis/diffcsp-pp_crystals_results.csv",
    #     "--mp_hull_path", "datasets/mp_hull/2024-08-07-ppd-mp.pkl",
    #     "--sample_size", "500",
    #     "--max_steps", "2500",
    #     "--dft_threshold", "0.5",
    #     "--output_dir", "chgnet_results_diffcsp-pp",
    #     "--un_only"
    # ],
    # [
    #     "python", 
    #     "eval_script/chgnet_process.py",
    #     "--cif_folder", "Generate_crystals/ADiT_crystals_mp20",
    #     "--csv_file", "Generate_crystals_flowmm_aligned_analysis/ADiT_crystals_mp20_results.csv",
    #     "--mp_hull_path", "datasets/mp_hull/2024-08-07-ppd-mp.pkl",
    #     "--sample_size", "500",
    #     "--max_steps", "2500",
    #     "--dft_threshold", "0.5",
    #     "--output_dir", "chgnet_results_ADiT",
    #     "--un_only"
    # ],
    # [
    #     "python", 
    #     "eval_script/chgnet_process.py",
    #     "--cif_folder", "Generate_crystals/flowmm_crystals",
    #     "--csv_file", "Generate_crystals_flowmm_aligned_analysis/flowmm_crystals_results.csv",
    #     "--mp_hull_path", "datasets/mp_hull/2024-08-07-ppd-mp.pkl",
    #     "--sample_size", "500",
    #     "--max_steps", "2500",
    #     "--dft_threshold", "0.5",
    #     "--output_dir", "./chgnet_results_flowmm",
    #     "--un_only"
    # ],
    # [
    #     "python", 
    #     "eval_script/chgnet_process.py",
    #     "--cif_folder", "Generate_crystals/CrystalDiT_crystals",
    #     "--csv_file", "Generate_crystals_flowmm_aligned_analysis/CrystalDiT_crystals_results.csv",
    #     "--mp_hull_path", "datasets/mp_hull/2024-08-07-ppd-mp.pkl",
    #     "--sample_size", "500",
    #     "--max_steps", "2500",
    #     "--dft_threshold", "0.5",
    #     "--output_dir", "chgnet_results_CrystalDiT_seed222",
    #     "--un_only",
    #     "--random_seed", "222"
    # ],
    [
        "python", 
        "eval_script/chgnet_process.py",
        "--cif_folder", "crystaldit_mpts52_crystals_ma52/checkpoint_epoch_38000_generated",
        "--csv_file", "crystaldit_mpts52_crystals_ma52_flowmm_aligned_analysis/checkpoint_epoch_38000_generated_results.csv",
        "--mp_hull_path", "datasets/mp_hull/2024-08-07-ppd-mp.pkl",
        "--sample_size", "500",
        "--max_steps", "2500",
        "--dft_threshold", "0.5",
        "--output_dir", "chgnet_results_CrystalDiT_mpts52_ep38000_seed222",
        "--un_only",
        "--random_seed", "222"
    ],  # CrystalDiT_mpts52
]
""" chgnet relaxation 
for i, cmd in enumerate(chgnet_cmds, start=1):
    print("--------------------------------------------------")
    print(f"Running command {i}/{len(chgnet_cmds)}")
    print(" ".join(cmd))
    print("--------------------------------------------------")
    
    try:
        subprocess.run(cmd, check=True)
        print(f"Command {i} finished successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Command {i} failed with return code {e.returncode}.")
        print("Continue to next command...")
    print("--------------------------------------------------")
"""

create_traj_cmds = [
    # [
    #     "python",
    #     "eval_script/create_traj_for_ehull.py",
    #     "--input-dir", "chgnet_results_CrystalDiT_seed222/dft_un",
    #     "--output-dir", "chgnet_results_CrystalDiT_seed222/dft_un",
    #     "--verbose"
    # ],  # mp-20
    [
        "python",
        "eval_script/create_traj_for_ehull.py",
        "--input-dir", "chgnet_results_CrystalDiT_mpts52_ep38000_seed123/dft_un",
        "--output-dir", "chgnet_results_CrystalDiT_mpts52_ep38000_seed123/dft_un",
        "--verbose"
    ],  # mpts-52
]
""" create traj file 
for i, cmd in enumerate(create_traj_cmds, start=1):
    print("--------------------------------------------------")
    print(f"Running command {i}/{len(create_traj_cmds)}")
    print(" ".join(cmd))
    print("--------------------------------------------------")
    
    try:
        subprocess.run(cmd, check=True)
        print(f"Command {i} finished successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Command {i} failed with return code {e.returncode}.")
        print("Continue to next command...")
    print("--------------------------------------------------")
"""

after_vasp_cmds = [
    # [
    #     "python", "eval_script/dft_post_processor.py",
    #     "--chgnet_csv", "chgnet_results_CrystalDiT_seed222/chgnet_results.csv",
    #     "--dft_results_folder", "chgnet_results_CrystalDiT_seed222",
    #     "--original_csv_file", "Generate_crystals_flowmm_aligned_analysis/CrystalDiT_crystals_results.csv",
    #     "--mp_hull_path", "datasets/mp_hull/2024-08-07-ppd-mp.pkl",
    #     "--output_dir", "chgnet_results_CrystalDiT_seed222/final_sun",
    #     "--un_only"
    # ]  # mp-20
    [
        "python", "eval_script/dft_post_processor.py",
        "--chgnet_csv", "chgnet_results_CrystalDiT_mpts52_ep38000_seed123/chgnet_results.csv",
        "--dft_results_folder", "chgnet_results_CrystalDiT_mpts52_ep38000_seed123",
        "--original_csv_file", "crystaldit_mpts52_crystals_ma52_flowmm_aligned_analysis/checkpoint_epoch_38000_generated_results.csv",
        "--mp_hull_path", "datasets/mp_hull/2024-08-07-ppd-mp.pkl",
        "--output_dir", "chgnet_results_CrystalDiT_mpts52_ep38000_seed123/final_sun",
        "--un_only"
    ]  # mpts-52
]
""" dft post processor 
for i, cmd in enumerate(after_vasp_cmds, start=1):
    print("--------------------------------------------------")
    print(f"Running command {i}/{len(after_vasp_cmds)}")
    print(" ".join(cmd))
    print("--------------------------------------------------")
    
    try:
        subprocess.run(cmd, check=True)
        print(f"Command {i} finished successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Command {i} failed with return code {e.returncode}.")
        print("Continue to next command...")
    print("--------------------------------------------------")
"""


extract_dft_cifs_cmds = [
    [
        "python",
        "eval_script/extract_dft_cifs.py",
        "--report", "chgnet_results_CrystalDiT/final_sun/final_evaluation_report.csv",
        "--out", "dft_cifs/CrystalDiT_mp20/"
    ],
    # [
    #     "python", "eval_script/extract_dft_cifs.py",
    #     "--report", "chgnet_results_CrystalDiT_mpts52_ep38000_seed123/final_sun/final_evaluation_report.csv",
    #     "--chgnet_csv", "chgnet_results_CrystalDiT_mpts52_ep38000_seed123/chgnet_results.csv",
    #     "--dft_dir", "chgnet_results_CrystalDiT_mpts52_ep38000_seed123",
    #     "--source", "both",
    #     "--out", "dft_cifs/CrystalDiT_mpts52_ep38000_seed123/"
    # ],  # 同时与 traj 交叉校验（确认 CSV 无损）
]
""" extract dft cifs """
for i, cmd in enumerate(extract_dft_cifs_cmds, start=1):
    print("--------------------------------------------------") 
    print(f"Running command {i}/{len(extract_dft_cifs_cmds)}")
    print(" ".join(cmd))
    print("--------------------------------------------------")
    
    try:
        subprocess.run(cmd, check=True)
        print(f"Command {i} finished successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Command {i} failed with return code {e.returncode}.")
        print("Continue to next command...")
    print("--------------------------------------------------")