"""GaussianRunner"""


import os
import subprocess as sp
import time
from multiprocessing import cpu_count
from multiprocessing.pool import ThreadPool


class GaussianRunner(object):
    def __init__(self, command="g16", cpu_num=None, nproc=4, keywords='', solution=False):
        self.command = command
        self.cpu_num = cpu_num if cpu_num else cpu_count()
        self.nproc = nproc
        self.thread_num = self.cpu_num//self.nproc
        self.keywords = keywords
        self.solution = solution

    def _logging(self, *message):
        localtime = time.asctime(time.localtime(time.time()))
        print(localtime, 'GaussianRunner', *message)

    def runCommand(self, command, inputstr=None):
        try:
            output = sp.check_output(command.split(), input=(
                inputstr.encode() if inputstr else None)).decode('utf-8')
        except sp.CalledProcessError as e:
            output = e.output.decode('utf-8')
            self._logging("ERROR: Run command", command)
        return output

    def runGaussianFunction(self, fileformat):
        if fileformat == 'input':
            function = self.runGaussianFromInput
        elif fileformat == 'smiles':
            function = self.runGaussianFromSMILES
        else:
            def function(filename): return self.runGaussianFromType(
                filename, fileformat)
        return function

    def generateLOGfilename(self, inputformat, inputlist):
        if inputformat == 'input':
            outputlist = range(len(inputlist))
        elif inputformat == 'smiles':
            outputlist = [x.replace('/', '／') .replace('\\', '＼')
                          for x in inputlist]
        else:
            outputlist = [os.path.splitext(x)[0] for x in inputlist]
        outputlist = [f'{x}.log' for x in outputlist]
        return outputlist

    def runGaussianInParallel(self, inputtype, inputlist, outputlist=None):
        inputtype = inputtype.lower()
        function = self.runGaussianFunction(inputtype)
        if outputlist is None:
            outputlist = self.generateLOGfilename(inputtype, inputlist)
        with ThreadPool(self.thread_num) as pool:
            results = pool.imap(function, inputlist)
            for outputfile, result in zip(outputlist, results):
                with open(outputfile, 'w') as f:
                    print(result, file=f)
        return outputlist

    def runGaussianFromInput(self, inputstr):
        output = self.runCommand(self.command, inputstr=inputstr)
        return output

    def runGaussianFromGJF(self, filename):
        with open(filename) as f:
            output = self.runGaussianFromInput(f.read())
        return output

    def runGaussianWithOpenBabel(self, obabel_command):
        inputstr = self.runCommand(obabel_command)
        inputstr = self.generateGJF(inputstr)
        output = self.runGaussianFromInput(inputstr)
        return output

    def runGaussianFromType(self, filename, fileformat):
        obabel_command = f'obabel -i {fileformat} {filename} -ogjf'
        return self.runGaussianWithOpenBabel(obabel_command)

    def runGaussianFromSMILES(self, SMILES):
        obabel_command = f'obabel -:{SMILES} --gen3d -ogjf'
        return self.runGaussianWithOpenBabel(obabel_command)

    def generateGJF(self, gaussianstr):
        keywords = f'%nproc={self.nproc}\n# {self.keywords} {" scrf=smd " if self.solution else ""}'
        s = gaussianstr.split('\n')
        s[0] = keywords
        s[2] = 'Run automatically by GaussianRunner'
        return '\n'.join(s)
