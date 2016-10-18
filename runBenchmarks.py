#!/usr/bin/env python3

# Copyright (c) 2016, Intel Corporation

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Intel Corporation nor the names of its contributors
#       may be used to endorse or promote products derived from this software
#       without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

# Instructions:
#   - JAVA_HOME should be set to default java installation
#   - Scala installation or build folders should start with 'scala' followed by the version number: 
#       'scala-2.12.x-src'
#   - Benchmark files should be located in the same folder as this script and the Instruments.scala
#   - Benchmarks should implement the Benchmark abtract class/trait
#   - Benchmark files should follow the naming convention: {Sc|Ja}BM<NAME>.{scala|java}
#   - Class to be benchmarked has to have the same name as the .java/.scala file
#   - Benchmarks with the same <NAME> will have their data grouped in the same worksheet
#   - Previous 

import os
import re
import sys
import glob
import math
import shutil
import filecmp
import argparse
import datetime
import xlsxwriter
import subprocess

def main():
    # Parse arguments
    args = parse_args()

    # Clear subfolders, xlxs and csv files from previous run(s)
    #TODO: clear all the files in advance is very dangerous, disable?
    # clear_files_folders()

    # Instrumentation shim file(s)
    inst_files = ['Instruments.scala']

    # Pack Scala and Java build and run options
    build_run_ops = get_build_run_ops()

    # Obtain benchmarks names
    benchmarks = get_benchmarks(inst_files)

    #TODO: everything below this line

    # Run benchmarks in individual folders and move generated csv files to main folder
    run_benchmarks(inst_files, benchmarks, build_run_ops, args)

    # Combine all spreadsheets in one
    combine_spreadsheets(args)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-h','--heap_size', default=28, type=int,
                        help='Java heap sizes to be used in GBs, default: 28GB')
    parser.add_argument('-M', '--max_size', default=1000000000, type=int,
                        help='max elements per benchmark, default: 1,000,000,000')
    parser.add_argument('-m', '--min_size', default=1000, type=int,
                        help='min elements per benchmark, default: 1,000')
    parser.add_argument('-t', '--run_time', default=300, type=int,
                        help='run time for each size in seconds, default: 300')
    parser.add_argument('-s', '--scala_base_path', default='',
                        help='Base path to scala installations or builds')

    args = parser.parse_args()

    return args

# def clear_files_folders():
#     for c in os.listdir():
#         if os.path.isdir(c):
#             shutil.rmtree(c)
#         elif c.endswith('.csv') or c.endswith('.xlsx') or c.endswith('.class'):
#             os.remove(c)

def get_build_run_ops():
    java_build_run_ops = get_java_build_run_ops()
    scala_build_run_ops = get_scala_build_run_ops(args.scala_base_path)
    return {'java': java_build_run_ops, 'scala': scala_build_run_ops} 

def get_java_build_run_ops():
    java_path = os.environ['JAVA_HOME']

    java_ver = java_path.split('/')[-1].split('-')[1]

    if not java_path.endswith('-oracle') or not os.path.isdir(java_path):
        print('Default Java version found in {}, should be Oracle JDK.')
        sys.exit(2)

    bin_path = os.path.join(java_path, '/bin/java')

    return [{'bin': bin_path, 'comp': bin_path + 'c', 'tag': 'J' + java_ver}]

def get_scala_build_run_ops(base_path):
    if base_path == '' or not os.path.isdir(base_path):
        print('Base path to Scala installation/build(s) can not be found.')
        sys.exit(2)

    scala_build_run_ops = []

    for scala_folder in glob.glob(os.path.join(base_path, 'scala*/')):
        scal_ver = scala_folder.split('/')[-2].split('-')[1]

        # Test if folder is a plain installation or a local build
        if os.path.exists(os.path.join(scala_folder, 'bin/')):
            bin_path = os.path.join(scala_folder, 'bin/scala')
        elif os.path.exists(os.path.join(scala_folder, 'build/')):
            bin_path = os.path.join(scala_folder, 'build/pack/bin/scala')

        temp = {'bin': bin_path, 'comp': bin_path + 'c', 'tag': 'S' + scal_ver}

        scala_build_run_ops.append(temp)

    return scala_build_run_ops

def get_benchmarks(inst_files):
    java_bms = sorted(glob.glob('*.java'))

    # Filter out instrumentation source files
    scala_bms = [x for x in sorted(glob.glob('*.scala')) if x not in inst_files]

    return {'java': java_bms, 'scala': scala_bms}

def run_benchmarks(inst_files, benchmarks, build_run_ops, args):
    bm_number = 1
    total = len(benchmarks['java'])*len(build_run_ops['java']) + 
            len(benchmarks['scala'])*len(build_run_ops['scala'])

    for lang in ['java', 'scala']:
        files = benchmarks[lang]

        for f in files:
            name = f.replace('.' + lang, '')    # Removing extension

            # Create benchmark folder and copy files
            if os.path.isdir(name):
                shutil.rmtree(name)               

            os.mkdir(name)
            shutil.copy(f, name)
            for inst_file in inst_files:
                shutil.copy(inst_file, name)
            for jfc in glob.glob('*.jfc'):
                shutil.copy(jfc, name)

            # Move to this benchmark directory
            os.chdir(name)

            # Build/run instrumentation/benchmark for each build/run option
            for lang_ops in build_run_ops[lang]:
                # Build instrumentation and benchmark files
                build_files(inst_files, f, lang_ops['comp'])

                # Run benchmark with different options/heap sizes
                run_benchmark(lang_ops['bin'], lang_ops['tag'], name, args,
                              bm_number, total)
                
                # Delete generated class files
                delete_class_files()

                # Increase benchmark counter
                bm_number += 1

            # Move results to main folder
            move_csv_files_back()

            # Go back to main directory
            os.chdir('..')

def build_files(inst_files, f, comp):
    # Build instrumentation ('scalac Instrumentation.java')
    for inst in inst_files:
        if comp.endswith('scalac'):
            subprocess.call('{} {}'.format(comp, inst), shell=True)
        else:            
            subprocess.call('scalac {}'.format(inst), shell=True)

    # Build benchmark ('javac file.java' or 'scalac file.scala')
    subprocess.call('{} {}'.format(comp, f), shell=True)

def run_benchmark(binary, tag, name, args, bm_number, total):
    cmd = create_cmd(binary, tag, name, args)

    output_filename = '{}_{}.txt'.format(name, tag)

    with open(output_filename, 'w') as output_file:
        # Print only short command, not full path to the command
        short_binary = binary.split('/')[-1]
        short_cmd = [short_binary, name, tag]

        print(datetime.datetime.now().strftime('%c '), end='') # cmd start time
        print('({:3}/{}) {}'.format(bm_number, total, ' '.join(short_cmd)))
        bm_number += 1

        try:
            subprocess.check_call(' '.join(cmd), shell=True, 
                                  stdout=output_file, stderr=output_file)
        except KeyboardInterrupt:
            print('Benchmark stopped by the user')
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            print('Benchmark failed with error code: {}'.format(e.returncode))
            print('Check output log {}/{}'.format(name, output_filename))
            sys.exit(2)

def create_cmd(binary, tag, name, args):
    cmd = []
    cmd.append(binary)

    if binary.endswith('java'):
        lang_mod = ''
    elif binary.endswith('scala'):
        lang_mod = '-J'

    cmd.append('{}-Xms{}g'.format(lang_mod, args.heap_size))
    cmd.append('{}-Xmx{}g'.format(lang_mod, args.heap_size))

    cmd.append('-cp .')     # So Scala can find the JFR file

    cmd.append('Instruments')

    cmd.append(name)

    cmd.append(args.min_size)

    cmd.append(args.max_size)

    cmd.append(args.run_time)  # seconds

    cmd.append(tag)

    return cmd

def delete_class_files():
    for f in glob.glob('*.class'):
        os.remove(f)

def move_csv_files_back():
    for f in glob.glob('*.csv'):
        shutil.move(f, '..')

def combine_spreadsheets(args):
    # length of each data block: 1 line per size + tag line + header line
    length = (math.log10(args.max_size/args.min_size) + 1) + 2

    # {name:{tag1:[[Runs], [Ops], [Times/run], [Times/op]], tag2:[]}, name2:{} }}
    benchmarks = {}

    # Extract data from csv files
    for csv_file in glob.glob('*.csv'):
        bm_name = csv_file.replace('.csv', '').split('BM')[1]

        if bm_name not in benchmarks:
            benchmarks[bm_name] = {}

        benchmark = benchmarks[bm_name]

        with open(csv_file) as f:
            for line_n, line in enumerate(f):
                # Skip header line
                if line_n % length == 0:
                    # Tag line
                    tag = line.strip()
                    benchmark[tag] = [[], [], [], []]
                elif line_n % length > 1:
                    # Skip Size/log(size) columns
                    data = line.strip().split(',')[2:]

                    for n, d in enumerate(data):
                        benchmark[tag][n].append(d)

        os.remove(csv_file)

    # Write aggregated data to one file
    with xlsxwriter.Workbook('benchmarks.xlsx', {'strings_to_numbers': True}) as wb:
        merge_format = wb.add_format({'align': 'center'})

        for bm_name, benchmark in benchmarks.items():
            ws = wb.add_worksheet(bm_name)
            n_tags = len(benchmark)

            # Write header line
            ws.merge_range(0, n_tags*0+1, 0, n_tags*1, 'Runs in {} secs'.format(args.run_time), merge_format)
            ws.merge_range(0, n_tags*1+1, 0, n_tags*2, 'Ops in {} secs'.format(args.run_time), merge_format)
            ws.merge_range(0, n_tags*2+1, 0, n_tags*3, 'Time/run (us)', merge_format)
            ws.merge_range(0, n_tags*3+1, 0, n_tags*4, 'Time/Op (us)', merge_format)

            # Write tags
            ws.write(1, 0, 'Size')

            tags = sorted(benchmark.keys())

            for mag_n in range(4):
                # Each tag repeats once per magnitude
                for tag_n, tag in enumerate(tags):
                    ws.write(1, 1+tag_n+mag_n*len(tags), tag)

            # write data lines (first column is size info)
            size = args.min_size
            row_offset = 0

            while size <= args.max_size:
                ws.write(2+row_offset, 0, size)

                for mag_n in range(4):
                    for tag_n, tag in enumerate(tags):
                        data = benchmark[tag][mag_n]
                        ws.write(2+row_offset, 1+tag_n+mag_n*len(tags), data)

                size *= 10
                row_offset += 1

if __name__ == '__main__':
    main()