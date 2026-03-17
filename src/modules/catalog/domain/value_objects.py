"""
Catalog domain value objects.

Contains immutable types that represent domain concepts without
identity. Part of the domain layer — zero infrastructure imports.
"""

import enum


class MediaProcessingStatus(str, enum.Enum):
    """Finite state machine (FSM) for media file processing lifecycle.

    Describes exclusively the business states of a media file's lifecycle,
    independent of any infrastructure details.

    States:
        PENDING_UPLOAD: Awaiting the client to upload the original file.
        PROCESSING: File uploaded; background processing in progress.
        COMPLETED: Processing finished; media is ready for use.
        FAILED: Processing failed (corrupted file or unsupported format).
    """

    PENDING_UPLOAD = "PENDING_UPLOAD"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
