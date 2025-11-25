class FixedWidthError(Exception):
    pass

class FileError(FixedWidthError): pass
class FileReadError(FileError): pass
class FileWriteError(FileError): pass
class EmptyFileError(FileError): pass

class StructureError(FixedWidthError): pass
class LineLengthMismatch(StructureError): pass


class ValidationError(FixedWidthError): pass
class HeaderValidationError(ValidationError): pass
class TransactionValidationError(ValidationError): pass
class FooterValidationError(ValidationError): pass

class RecordError(FixedWidthError): pass
class InvalidRecordIndexError(RecordError): pass
class ReadOnlyFieldUpdateError(RecordError): pass
class AtomicUpdateError(RecordError): pass
class AmountTooLargeError(RecordError): pass
class MaxTransactionLimitError(RecordError): pass
