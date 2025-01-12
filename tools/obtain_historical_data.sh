#!/bin/bash
#SBATCH -A p30791
#SBATCH -p normal
#SBATCH -t 24:00:00
#SBATCH -N 1
#SBATCH -n 1
#SBATCH --mem=1G
#SBATCH --job-name=bs_data
#SBATCH --mail-user=sayarenedennis@northwestern.edu
#SBATCH --mail-type=END,FAIL
#SBATCH --output=/projects/p30791/out/obtain_historical_data.out

export PATH="/software/miniconda3/4.12.0/bin:$PATH"
source activate book-rec

cd /projects/p30791/book-rec/

python tools/obtain_historical_data.py

