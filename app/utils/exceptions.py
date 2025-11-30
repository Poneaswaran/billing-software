class AppError(Exception):
    """Base class for other exceptions"""
    pass

class PrinterError(AppError):
    """Raised when printer fails"""
    pass

class DatabaseError(AppError):
    """Raised when database operation fails"""
    pass

class ValidationError(AppError):
    """Raised when validation fails"""
    pass
