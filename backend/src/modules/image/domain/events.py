"""Image domain events.

The image module currently does not emit any concrete domain events
(parity with the legacy ``image_backend`` microservice, which used SSE
pub/sub directly for status broadcast rather than the outbox). The
abstract base is declared here so that future events — for example
``StorageObjectProcessedEvent`` consumed by catalog / activity for
auto-attaching a thumbnail to a product — drop in without restructuring
the module.

Validation + ``aggregate_id`` auto-fill come from
:class:`src.shared.interfaces.entities.ModuleDomainEvent`.
"""

from dataclasses import dataclass

from src.shared.interfaces.entities import ModuleDomainEvent


@dataclass
class ImageEvent(ModuleDomainEvent, abstract=True):
    """Intermediate base for all image module domain events."""

    aggregate_type: str = "image"
