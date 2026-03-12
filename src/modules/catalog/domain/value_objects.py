import enum

class MediaProcessingStatus(str, enum.Enum):
    """
    State Machine (FSM) для асинхронной загрузки файлов (Claim Check Pattern).
    """

    PENDING_UPLOAD = "PENDING_UPLOAD"  # Выдан Presigned URL, ждем загрузки от фронтенда
    PROCESSING = "PROCESSING"  # Фронт подтвердил загрузку, TaskIQ воркер обрабатывает
    COMPLETED = "COMPLETED"  # Обработка (ресайз/WebP) завершена успешно
    FAILED = "FAILED"  # Ошибка (неверный формат, битый файл)
