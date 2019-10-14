class TranslatorException(Exception):
    pass

class VMSyntaxError(TranslatorException):
    pass

class TooManyStaticVariableError(TranslatorException):
    pass