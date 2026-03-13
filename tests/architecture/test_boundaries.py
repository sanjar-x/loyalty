# tests/architecture/test_boundaries.py
import pytest
from pytest_archon import archrule

pytestmark = pytest.mark.architecture


def test_domain_layer_is_pure():
    """
    [Clean Architecture] Правило чистого Домена:
    Слой Domain является ядром. Он НЕ ИМЕЕТ ПРАВА ничего знать о внешних слоях:
    Application, Infrastructure, Presentation или глобальных настройках (Bootstrap).
    """
    (
        archrule("domain_independence")
        .match("src.modules.*.domain.*")
        .should_not_import("src.modules.*.application.*")
        .should_not_import("src.modules.*.infrastructure.*")
        .should_not_import("src.modules.*.presentation.*")
        .should_not_import("src.api.*")
        .should_not_import("src.bootstrap.*")
        .check("src")
    )


def test_application_layer_boundaries():
    """
    [Clean Architecture] Правило слоя Application (Use Cases / CQRS):
    Слой Application управляет бизнес-процессами. Он может импортировать Domain,
    но НЕ ДОЛЖЕН зависеть от деталей реализации (Infrastructure) и (Presentation).
    """
    (
        archrule("application_independence")
        .match("src.modules.*.application.*")
        .exclude("src.modules.catalog.application.queries.get_category_tree")
        .should_not_import("src.modules.*.infrastructure.*")
        .should_not_import("src.modules.*.presentation.*")
        .should_not_import("src.api.*")
        .check("src")
    )


def test_infrastructure_does_not_import_presentation():
    """
    [Clean Architecture] Правило слоя Infrastructure:
    Инфраструктура (репозитории, S3 адаптеры, модели БД) не должна зависеть
    от веб-роутеров (Presentation) и глобальных эндпоинтов (API).
    """
    (
        archrule("infrastructure_independence")
        .match("src.modules.*.infrastructure.*")
        .should_not_import("src.modules.*.presentation.*")
        .should_not_import("src.api.*")
        .check("src")
    )


def test_modular_monolith_strict_isolation():
    """
    [Modular Monolith] Правило изоляции модулей:
    Модули (Catalog, Storage) должны быть слабо связаны.
    Общение между ними допускается ТОЛЬКО через публичные интерфейсы (shared/interfaces)
    или публичные фасады (presentation.facade.
    """
    (
        archrule("storage_internals_are_private_from_catalog")
        .match("src.modules.catalog.*")
        .should_not_import("src.modules.storage.infrastructure.*")
        .should_not_import("src.modules.storage.domain.*")
        .should_not_import("src.modules.storage.application.*")
        .check("src")
    )

    (
        archrule("catalog_internals_are_private_from_storage")
        .match("src.modules.storage.*")
        .should_not_import("src.modules.catalog.infrastructure.*")
        .should_not_import("src.modules.catalog.domain.*")
        .should_not_import("src.modules.catalog.application.*")
        .should_not_import("src.modules.catalog.presentation.*")
        .check("src")
    )


def test_shared_kernel_is_independent():
    """
    [DDD] Правило Shared Kernel (Общее ядро):
    Папка src/shared/ содержит общие интерфейсы и абстракции (IUnitOfWork, порты).
    Она является фундаментом и НЕ ДОЛЖНА зависеть ни бизнес-модуля.
    """
    (
        archrule("shared_kernel_independence")
        .match("src.shared.*")
        .should_not_import("src.modules.catalog.*")
        .should_not_import("src.modules.storage.*")
        .check("src")
    )
