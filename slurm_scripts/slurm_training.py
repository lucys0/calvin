import argparse
import datetime
import os
from pathlib import Path
import stat
import subprocess

import git
from git import Repo
import numpy as np
from setuptools import sandbox

default_log_dir = f"/home/{os.environ['USER']}/logs" if "USER" in os.environ else "/tmp"
if default_log_dir == "/tmp":
    print("CAUTION: logging to /tmp")
parser = argparse.ArgumentParser(description="Parse slurm parameters and hydra config overrides")

parser.add_argument("--script", type=str, default="./sbatch_lfp.sh")
parser.add_argument("--train_file", type=str, default="../calvin_models/calvin_agent/training.py")
parser.add_argument("-l", "--log_dir", type=str, default=default_log_dir)
parser.add_argument("-j", "--job_name", type=str, default="play_training")
parser.add_argument("-g", "--gpus", type=int, default=1)
parser.add_argument("--mem", type=int, default=0)  # 0 means no memory limit
parser.add_argument("--cpus", type=int, default=8)
parser.add_argument("--days", type=int, default=1)
parser.add_argument("-v", "--venv", type=str)
parser.add_argument("-p", "--partition", type=str, default="alldlc_gpu-rtx2080")
parser.add_argument("--no_clone", action="store_true")
args, unknownargs = parser.parse_known_args()


assert np.all(["gpu" not in arg for arg in unknownargs])
assert np.all(["hydra.run.dir" not in arg for arg in unknownargs])
assert np.all(["log_dir" not in arg for arg in unknownargs])
assert np.all(["hydra.sweep.dir" not in arg for arg in unknownargs])

log_dir = Path(args.log_dir).absolute() / f'{datetime.datetime.now().strftime("%Y-%m-%d/%H-%M-%S")}_{args.job_name}'
os.makedirs(log_dir)
args.script = Path(args.script).absolute()
args.train_file = Path(args.train_file).absolute()


def create_git_copy(repo_src_dir, repo_target_dir):
    repo = Repo(repo_src_dir)
    repo.clone(repo_target_dir)
    orig_cwd = os.getcwd()
    os.chdir(repo_target_dir)
    sandbox.run_setup("setup_local.py", ["develop", "--install-dir", "."])
    os.chdir(orig_cwd)


if not args.no_clone:
    repo_src_dir = Path(__file__).absolute().parents[1]
    repo_target_dir = log_dir / "calvin_models/calvin_agent"
    create_git_copy(repo_src_dir, repo_target_dir)

    args.script = repo_target_dir / os.path.relpath(args.script, repo_src_dir)
    args.train_file = repo_target_dir / os.path.relpath(args.train_file, repo_src_dir)

# if not args.cpus:
# args.cpus = args.gpus * 8

job_opts = {
    "script": f"{args.script.as_posix()} {args.venv} {args.train_file.as_posix()} {log_dir.as_posix()} {args.gpus} {' '.join(unknownargs)}",
    "partition": args.partition,
    "mem": args.mem,
    "ntasks-per-node": args.gpus,
    "cpus_per_task": args.cpus,
    "gres": f"gpu:{args.gpus}",
    "output": os.path.join(log_dir, "%x.%N.%j.out"),
    "error": os.path.join(log_dir, "%x.%N.%j.err"),
    "job_name": args.job_name,
    "mail-type": "END,FAIL",
    "time": f"{args.days}-00:00",
}


def submit_job(job_info):
    # Construct sbatch command
    slurm_cmd = ["sbatch"]
    for key, value in job_info.items():
        # Check for special case keys
        if key == "cpus_per_task":
            key = "cpus-per-task"
        if key == "job_name":
            key = "job-name"
        elif key == "script":
            continue
        slurm_cmd.append("--%s=%s" % (key, value))
    slurm_cmd.append(job_info["script"])
    print("Generated slurm batch command: '%s'" % slurm_cmd)

    # Run sbatch command as subprocess.
    try:
        sbatch_output = subprocess.check_output(slurm_cmd)
        create_resume_script(slurm_cmd)
    except subprocess.CalledProcessError as e:
        # Print error message from sbatch for easier debugging, then pass on exception
        if sbatch_output is not None:
            print("ERROR: Subprocess call output: %s" % sbatch_output)
        raise e

    print(sbatch_output.decode("utf-8"))


def create_resume_script(slurm_cmd):
    file_path = os.path.join(log_dir, "resume_training.sh")
    with open(file_path, "w") as file:
        file.write("#!/bin/bash\n")
        file.write(" ".join(slurm_cmd))
    st = os.stat(file_path)
    os.chmod(file_path, st.st_mode | stat.S_IEXEC)


submit_job(job_opts)
