class AssemblyInstruction:
    def __init__(self):
        pass

    @staticmethod
    def parse(assembly_str):
        tmp = assembly_str.split("//")
        if len(tmp) == 0:
            return None
        assembly_str = tmp[0]
        if assembly_str[0] == "@":
            return AssemblyA(assembly_str[1:])
        elif assembly_str[0] == "(":
            return AssemblyLabel(assembly_str[1:-1])
        else:
            return AssemblyI(assembly_str)
    
    def to_string(self):
        raise NotImplementedError
    
    def get_label(self):
        raise NotImplementedError

    def set_label(self, address):
        raise NotImplementedError

    def type(self):
        raise NotImplementedError

class AssemblyI(AssemblyInstruction):
    def __init__(self, arithmetic = "0", branch = None):
        self.arithmetic = arithmetic
        self.branch = branch
    
    def to_string(self):
        if self.branch is None:
            return self.arithmetic
        else:
            return self.arithmetic + ";" + self.branch
    
    def get_label(self):
        return None
    
    def set_label(self, address):
        pass

    def type(self):
        return "I"
    
    def __repr__(self):
        return "<Assembly   [" + self.to_string() + "] >"

class AssemblyA(AssemblyInstruction):
    def __init__(self, address):
        if address.isdigit():
            self.label = None
            self.address = int(address)
        else:
            self.label = address
            self.address = None

    def to_string(self):
        if self.label is None:
            return "@" + str(self.address)
        else:
            return "@" + self.label
        
    def get_label(self):
        return self.label
    
    def set_label(self, address):
        if self.label is not None:
            self.address = address
            self.label = None
    
    def type(self):
        return "A"

    def __repr__(self):
        return "<Assembly   [" + self.to_string() + "] >"

class AssemblyLabel(AssemblyInstruction):
    def __init__(self, label):
        self.label = label
    
    def to_string(self):
        return "(%s)" % self.label
    
    def get_label(self):
        return self.label
    
    def set_label(self, address):
        pass

    def type(self):
        return "L"

    def __repr__(self):
        return "<Assembly   [" + self.to_string() + "] >"