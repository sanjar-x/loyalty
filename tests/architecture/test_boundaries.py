from pytest_archon import archrule


def test_domain_layer_dependencies():
    """
    Доменный слой не должен зависеть ни от каких других слоев.
    (Clean Architecture: Dependency Rule)
    """
    rule = (
        archrule("domain_independence")
        .match("src.modules.*.domain*")
        .should_not_import("src.modules.*.application*")
        .should_not_import("src.modules.*.infrastructure*")
        .should_not_import("src.modules.*.presentation*")
    )
    rule.check("src")


def test_application_layer_dependencies():
    """
    Application слой управляет Use Cases.
    Он может зависеть от Domain, но не от Infrastructure (использует порты) или Presentation.
    """
    rule = (
        archrule("application_independence")
        .match("src.modules.*.application*")
        .should_not_import("src.modules.*.infrastructure*")
        .should_not_import("src.modules.*.presentation*")
    )
    rule.check("src")


def test_module_isolation():
    """
    Модули не должны напрямую ходить в инфраструктуру или домен друг друга.
    Например, catalog модуль не должен импортировать напрямую storage/infrastructure.
    """
    rule = (
        archrule("catalog_isolation_from_storage")
        .match("src.modules.catalog*")
        # Разрешено общаться только через shared/interfaces или фасады
        .should_not_import("src.modules.storage.infrastructure*")
        .should_not_import("src.modules.storage.domain*")
        .should_not_import("src.modules.storage.application.commands*")
        .should_not_import("src.modules.storage.application.queries*")
    )
    rule.check("src")
