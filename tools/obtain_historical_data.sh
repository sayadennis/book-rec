#!/bin/bash
#SBATCH -A p30791
#SBATCH -p short
#SBATCH -t 4:00:00
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --mem=1G
#SBATCH --job-name=2023
#SBATCH --mail-user=sayarenedennis@northwestern.edu
#SBATCH --mail-type=END,FAIL
#SBATCH --output=/projects/p30791/out/obtain_historical_data.out

module purge all
module load python-miniconda3/4.12.0
source activate book-rec

cd /projects/p30791/book-rec/

python tools/obtain_historical_data.py

