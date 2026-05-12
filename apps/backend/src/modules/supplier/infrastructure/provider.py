"""Dishka IoC providers for the Supplier bounded context."""

from dishka import Provider, Scope, provide
from dishka.dependency_source.composite import CompositeDependencySource

from src.modules.supplier.application.commands.activate_supplier import (
    ActivateSupplierHandler,
)
from src.modules.supplier.application.commands.create_supplier import (
    CreateSupplierHandler,
)
from src.modules.supplier.application.commands.deactivate_supplier import (
    DeactivateSupplierHandler,
)
from src.modules.supplier.application.commands.update_supplier import (
    UpdateSupplierHandler,
)
from src.modules.supplier.application.queries.get_supplier import GetSupplierHandler
from src.modules.supplier.application.queries.list_suppliers import ListSuppliersHandler
from src.modules.supplier.domain.interfaces import (
    ISupplierQueryService,
    ISupplierRepository,
)
from src.modules.supplier.infrastructure.query_service import SupplierQueryService
from src.modules.supplier.infrastructure.repositories.supplier import SupplierRepository
from src.shared.interfaces.supplier_directory import ISupplierDirectory


class SupplierProvider(Provider):
    supplier_repo: CompositeDependencySource = provide(
        SupplierRepository, scope=Scope.REQUEST, provides=ISupplierRepository
    )
    supplier_query_service: CompositeDependencySource = provide(
        SupplierQueryService, scope=Scope.REQUEST, provides=ISupplierQueryService
    )
    supplier_directory: CompositeDependencySource = provide(
        SupplierQueryService, scope=Scope.REQUEST, provides=ISupplierDirectory
    )
    create_supplier_handler: CompositeDependencySource = provide(
        CreateSupplierHandler, scope=Scope.REQUEST
    )
    update_supplier_handler: CompositeDependencySource = provide(
        UpdateSupplierHandler, scope=Scope.REQUEST
    )
    deactivate_supplier_handler: CompositeDependencySource = provide(
        DeactivateSupplierHandler, scope=Scope.REQUEST
    )
    activate_supplier_handler: CompositeDependencySource = provide(
        ActivateSupplierHandler, scope=Scope.REQUEST
    )
    get_supplier_handler: CompositeDependencySource = provide(
        GetSupplierHandler, scope=Scope.REQUEST
    )
    list_suppliers_handler: CompositeDependencySource = provide(
        ListSuppliersHandler, scope=Scope.REQUEST
    )
