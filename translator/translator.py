from .assembly import AssemblyI, AssemblyA, AssemblyLabel
from .exception import VMSyntaxError, TooManyStaticVariableError
import os

class TranslatorSingleFile:
    def __init__(self, namespace = "GlobalNameSpace"):
        self.namespace = namespace
        self.active_function = "global"
        self.local_label_counter = 0
        self.func_label_counter = 0
    
    def _setActiveFunc(self, funcname):
        self.active_function = funcname
        self.func_label_counter = 0

    def _genLocalLabel(self):
        ret = self.active_function + (".$local_label.%d" % self.local_label_counter)
        self.local_label_counter += 1
        return ret
    
    def _genFuncRet(self):
        ret = self.active_function + ("$ret.%d" % self.func_label_counter)
        self.func_label_counter += 1
        return ret
    
    def _parseArithmetic(self, op, args):
        ret = []
        if op in ["neg", "not"]:
            ret.extend([
                AssemblyA("SP"),
                AssemblyI("A=M-1")
            ])
            if op == "neg":
                ret.append( AssemblyI("D=-M") )
            else:
                ret.append( AssemblyI("D=!M") )
            ret.append( AssemblyI("M=D") )
            return ret
        # else
        ret.extend([
            AssemblyA("SP"),
            AssemblyI("M=M-1"),
            AssemblyI("A=M"),
            AssemblyI("D=M"),
            AssemblyI("A=A-1"),
        ])
        # data in M and D
        if op == "add":
            ret.append(AssemblyI("D=D+M"))
        elif op == "sub":
            ret.append(AssemblyI("D=M-D"))
        elif op == "gt":
            tmp_label = self._genLocalLabel()
            ret.extend([
                AssemblyI("D=M-D"),
                AssemblyA(tmp_label),
                AssemblyI("D", "JLE"),
                AssemblyI("D=-1"),
                AssemblyI("A=A+1"),
                AssemblyI("0", "JMP"),
                AssemblyLabel(tmp_label),
                AssemblyI("D=0"),
                AssemblyA("SP"),
                AssemblyI("A=M-1")
            ])
        elif op == "lt":
            tmp_label = self._genLocalLabel()
            ret.extend([
                AssemblyI("D=M-D"),
                AssemblyA(tmp_label),
                AssemblyI("D", "JGE"),
                AssemblyI("D=-1"),
                AssemblyI("A=A+1"),
                AssemblyI("0", "JMP"),
                AssemblyLabel(tmp_label),
                AssemblyI("D=0"),
                AssemblyA("SP"),
                AssemblyI("A=M-1")
            ])
        elif op == "eq":
            tmp_label = self._genLocalLabel()
            ret.extend([
                AssemblyI("D=M-D"),
                AssemblyA(tmp_label),
                AssemblyI("D", "JNE"),
                AssemblyI("D=-1"),
                AssemblyI("A=A+1"),
                AssemblyI("0", "JMP"),
                AssemblyLabel(tmp_label),
                AssemblyI("D=0"),
                AssemblyA("SP"),
                AssemblyI("A=M-1")
            ])
        elif op == "and":
            ret.append(AssemblyI("D=D&M"))
        elif op == "or":
            ret.append(AssemblyI("D=D|M"))
        ret.append(AssemblyI("M=D"))
        return ret

    def _parseMem(self, op, args):
        segment, offset = args
        segment = segment.lower()
        ret = []
        if op == "push":
            if segment in ["local", "argument", "this", "that"]:
                if segment == "local":
                    ret.append(AssemblyA("LCL"))
                elif segment == "argument":
                    ret.append(AssemblyA("ARG"))
                elif segment == "this":
                    ret.append(AssemblyA("THIS"))
                else:
                    ret.append(AssemblyA("THAT"))
                ret.extend([
                    AssemblyI("D=M"),
                    AssemblyA(offset),
                    AssemblyI("A=D+A"),
                    AssemblyI("D=M")
                    # load segment i to M
                ])
            elif segment == "constant":
                ret.extend([
                    AssemblyA(offset),
                    AssemblyI("D=A")
                ])
            elif segment == "static":
                ret.extend([
                    AssemblyA(self.namespace + "." + offset),
                    AssemblyI("D=M")
                ])
            elif segment == "temp":
                ret.extend([
                    AssemblyA("5"),
                    AssemblyI("D=A"),
                    AssemblyA(offset),
                    AssemblyI("A=D+A"),
                    AssemblyI("D=M")
                ])
            elif segment == "pointer":
                ret.extend([
                    AssemblyA("3"),
                    AssemblyI("D=A"),
                    AssemblyA(offset),
                    AssemblyI("A=D+A"),
                    AssemblyI("D=M")
                ])
            else:
                raise VMSyntaxError()

            ret.extend([
                AssemblyA("SP"),
                AssemblyI("A=M"),
                AssemblyI("M=D"),
                AssemblyA("SP"),
                AssemblyI("M=M+1")
            ])
        else:   # pop
            if segment in ["local", "argument", "this", "that"]:
                if segment == "local":
                    ret.append(AssemblyA("LCL"))
                elif segment == "argument":
                    ret.append(AssemblyA("ARG"))
                elif segment == "this":
                    ret.append(AssemblyA("THIS"))
                else:
                    ret.append(AssemblyA("THAT"))
                ret.extend([
                    AssemblyI("D=M"),
                    AssemblyA(offset),
                    AssemblyI("D=D+A"),
                ])
            elif segment == "static":
                ret.extend([
                    AssemblyA(self.namespace + "." + offset),
                    AssemblyI("D=A")
                ])
            elif segment == "temp":
                ret.extend([
                    AssemblyA("5"),
                    AssemblyI("D=A"),
                    AssemblyA(offset),
                    AssemblyI("D=D+A"),
                ])
            elif segment == "pointer":
                ret.extend([
                    AssemblyA("3"),
                    AssemblyI("D=A"),
                    AssemblyA(offset),
                    AssemblyI("D=D+A"),
                ])
            else:
                raise VMSyntaxError()
            ret.extend([
                # store dest temporarily
                AssemblyA("SP"),
                AssemblyI("A=M"),
                AssemblyI("M=D"),
                
                # move to stack top
                AssemblyI("A=A-1"),
                AssemblyI("D=M"),
                AssemblyI("A=A+1"),
                AssemblyI("A=M"),
                AssemblyI("M=D"),
                
                # pop
                AssemblyA("SP"),
                AssemblyI("M=M-1")
            ])
        return ret

    def _parseBranch(self, op, args):
        label = args[0]
        if op == "label":
            return [ AssemblyLabel(self.active_function + "$" + label) ]
        elif op == "goto":
            return [
                AssemblyA(self.active_function + "$" + label),
                AssemblyI("0", "JMP")
            ]
        else:   # if-goto
            return [
                AssemblyA("SP"),
                AssemblyI("M=M-1"),
                AssemblyI("A=M"),
                AssemblyI("D=M"),
                AssemblyA(self.active_function + "$" + label),
                AssemblyI("D", "JNE")
            ]

    def _parseFunc(self, op, args):
        if op == "function":
            self._setActiveFunc(args[0])
            ret = []
            ret.extend([
                AssemblyLabel(self.active_function),
                AssemblyA("SP"),
                AssemblyI("A=M")
            ])
            for _ in range(int(args[1])):
                ret.extend([
                    AssemblyI("M=0"),
                    AssemblyI("A=A+1")
                ])
            ret.extend([
                AssemblyI("D=A"),
                AssemblyA("SP"),
                AssemblyI("M=D")
            ])
            return ret
            
        elif op == "call":
            ret_label = self._genFuncRet()
            ret = [
                # RA
                AssemblyA(ret_label),
                AssemblyI("D=A"),
                AssemblyA("SP"),
                AssemblyI("A=M"),
                AssemblyI("M=D"),

                # ARG
                AssemblyA("ARG"),
                AssemblyI("D=M"),
                AssemblyA("R13"),
                AssemblyI("M=D"),

                # calc new ARG
                AssemblyA("SP"),
                AssemblyI("D=M"),
                AssemblyA(args[1]),
                AssemblyI("D=D-A"),
                AssemblyA("ARG"),
                AssemblyI("M=D"),   # set new ARG
            ]
            for it in ["LCL", "R13", "THIS", "THAT"]:   # push 4
                ret.extend([
                    AssemblyA(it),
                    AssemblyI("D=M"),
                    AssemblyA("SP"),
                    AssemblyI("M=M+1"),
                    AssemblyI("A=M"),
                    AssemblyI("M=D"),
                ])
            ret.extend([
                AssemblyA("SP"),
                AssemblyI("M=M+1"),
                AssemblyI("D=M"),   # new LCL
                AssemblyA("LCL"),
                AssemblyI("M=D"),
                AssemblyA(args[0]),
                AssemblyI("0", "JMP"),
                AssemblyLabel(ret_label)
            ])
            return ret
        else:   # return
            ret = [
                AssemblyA("LCL"),
                AssemblyI("D=M"),
                AssemblyA("5"),
                AssemblyI("A=D-A"),
                AssemblyI("D=M"),   # RA
                AssemblyA("R14"),
                AssemblyI("M=D"),   # put RA in R14

                AssemblyA("SP"),
                AssemblyI("A=M-1"),
                AssemblyI("D=M"),   # get ret Val
                AssemblyA("ARG"),
                AssemblyI("A=M"),
                AssemblyI("M=D"),   # put ret val

                AssemblyI("D=A+1"),
                AssemblyA("R13"),
                AssemblyI("M=D"),

                AssemblyA("LCL"),
                AssemblyI("A=M"),
            ]
            for it in ["THAT", "THIS", "ARG", "LCL"]:
                ret.extend([
                    AssemblyI("D=A-1"),
                    AssemblyA("SP"),
                    AssemblyI("M=D"),
                    AssemblyI("A=D"),
                    AssemblyI("D=M"),
                    AssemblyA(it),
                    AssemblyI("M=D"),
                    AssemblyA("SP"),
                    AssemblyI("A=M")
                ])
            ret.extend([
                AssemblyI("D=A-1"),
                AssemblyA("SP"),
                AssemblyI("M=D"),   # pop RA

                AssemblyA("R13"),
                AssemblyI("D=M"),   # arg + 1
                AssemblyA("SP"),
                AssemblyI("M=D"),   # set SP

                AssemblyA("R14"),   # get RA
                AssemblyI("A=M"),   # A = RA
                AssemblyI("0", "JMP")
            ])
            return ret

    def _parseLine(self, cmd):
        tmp = cmd.split("//")
        cmd = tmp[0]    # remove comment
        cmds = cmd.split()
        if len(cmds) == 0:
            return []
        op = cmds[0].lower()

        if op in ["add", "sub", "neg", "eq", "gt", "lt", "and", "or", "not"]:
            return self._parseArithmetic(op, cmds[1:])
        elif op in ["push", "pop"]:
            return self._parseMem(op, cmds[1:])
        elif op in ["label", "goto", "if-goto"]:
            return self._parseBranch(op, cmds[1:])
        elif op in ["function", "call", "return"]:
            return self._parseFunc(op, cmds[1:])
        else:
            raise VMSyntaxError()
    
    def parse(self, stream, namespace = None):
        lines = stream.read().split("\n")
        if namespace is not None:
            self.namespace = namespace
        self.active_function = "global"
        self.local_label_counter = 0
        self.func_label_counter = 0
        ret = []
        for line in lines:
            ret.extend(self._parseLine(line))
        return ret

class TranslatorLinker:
    def __init__(self, global_symbols = {}):
        self.symbols = {
            "SP": 0,
            "LCL": 1,
            "ARG": 2,
            "THIS": 3,
            "THAT": 4
        }
        for i in range(16):
            self.symbols["R%d" % i] = i
        self.symbols.update({
            "SCREEN": 16384,
            "KBD": 24576
        })
        self.symbols.update(global_symbols)
    
    def link(self, asm_list, ostream, keep_label=False):
        label_set = set()
        for namespace in asm_list.keys():
            for it in asm_list[namespace]:
                lb = it.get_label()
                if lb is not None:
                    label_set.add(lb)
        label_address = self.symbols.copy()
        line_counter = 0
        for namespace in asm_list.keys():
            for it in asm_list[namespace]:
                lb = it.get_label()
                if lb is not None:
                    if isinstance(it, AssemblyLabel):
                        label_address[lb] = line_counter
                    else:
                        line_counter += 1
                else:
                    line_counter += 1
        
        static_counter = 0
        for label in label_set:
            if label not in label_address:
                label_address[label] = 16 + static_counter
                static_counter += 1
        if static_counter > 240:
            raise TooManyStaticVariableError()
        for namespace in asm_list.keys():
            for it in asm_list[namespace]:
                if isinstance(it, AssemblyLabel):
                    continue
                if not keep_label:
                    lb = it.get_label()
                    if lb is not None:
                        it.set_label(label_address[lb])
                ostream.write(it.to_string() + "\n")
        return

class Translator:
    def __init__(self):
        self.file_list = []

    def append(self, filename, encoding="utf-8"):
        base = ".".join(os.path.basename(filename).split(".")[:-1])
        self.file_list.append((base, filename, encoding))
        return
    
    def translate(self, ostream, keep_label=False):
        ret = {}
        for namespace, filepath, encoding in self.file_list:
            tf = TranslatorSingleFile(namespace=namespace)
            ret[namespace] = tf.parse(open(filepath, "r", encoding=encoding))
        
        linker = TranslatorLinker()
        linker.link(ret, ostream, keep_label)
        return
