##	Training CALVIN on a Slurm Cluster
### Starting a training
```bash
$ cd $CALVIN_ROOT/slurm_scripts
$ python slurm_training.py --venv calvin_venv datamodule.root_data_dir=/path/to/dataset/
```
This assumes that `--venv calvin_venv` specifies a conda environment.
To use virtualenv instead, change line 18 of sbatch_lfp.sh accordingly.

All hydra arguments can be used as in the normal training.

Use the following optional command line arguments for slurm:
- `--log_dir`: slurm log directory
- `--job_name`: slurm job name
- `--gpus`: number of gpus
- `--mem`: memory
- `--cpus`: number of cpus
- `--days`: time limit in days
- `--partition`: name of slurm partition

The script will create a new folder in the specified log dir with a date tag and the job name.
This is done *before* the job is submitted to the slurm queue.
In order to ensure reproducibility, the current state of the calvin repository
is copied to the log directory at *submit time* and is
locally installed, such that you can schedule multiple trainings and there is no interference with
future changes to the repository.

### Resuming a training
Every job submission creates a `resume_training.sh` script in the log folder. To resume a training,
call `$ sh <PATH_TO_LOG_DIR>/resume_training.sh`.
