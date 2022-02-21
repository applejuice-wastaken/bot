class FlagOpenError(Exception):
    def __init__(self):
        super(FlagOpenError, self).__init__("File format of flag is not supported")
