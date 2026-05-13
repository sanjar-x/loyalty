"""Unit tests for ShippingProviderRegistry."""

import pytest

from src.modules.logistics.domain.exceptions import ProviderUnavailableError
from src.modules.logistics.domain.value_objects import (
    PROVIDER_CDEK,
    PROVIDER_YANDEX_DELIVERY,
)
from src.modules.logistics.infrastructure.services.registry import (
    ShippingProviderRegistry,
)
from tests.fakes.fake_logistics_providers import (
    FakeBookingProvider,
    FakeDocumentProvider,
    FakePickupPointProvider,
    FakeRateProvider,
    FakeTrackingPollProvider,
    FakeTrackingProvider,
)

pytestmark = pytest.mark.unit


class TestRegistryRegistration:
    def test_register_and_get_rate_provider(self):
        registry = ShippingProviderRegistry()
        provider = FakeRateProvider(code=PROVIDER_CDEK)
        registry.register_rate_provider(provider)
        assert registry.get_rate_provider(PROVIDER_CDEK) is provider

    def test_register_and_get_booking_provider(self):
        registry = ShippingProviderRegistry()
        provider = FakeBookingProvider(code=PROVIDER_CDEK)
        registry.register_booking_provider(provider)
        assert registry.get_booking_provider(PROVIDER_CDEK) is provider

    def test_register_and_get_tracking_provider(self):
        registry = ShippingProviderRegistry()
        provider = FakeTrackingProvider(code=PROVIDER_CDEK)
        registry.register_tracking_provider(provider)
        assert registry.get_tracking_provider(PROVIDER_CDEK) is provider

    def test_register_and_get_tracking_poll_provider(self):
        registry = ShippingProviderRegistry()
        provider = FakeTrackingPollProvider(code=PROVIDER_CDEK)
        registry.register_tracking_poll_provider(provider)
        assert registry.get_tracking_poll_provider(PROVIDER_CDEK) is provider

    def test_register_and_get_pickup_point_provider(self):
        registry = ShippingProviderRegistry()
        provider = FakePickupPointProvider(code=PROVIDER_CDEK)
        registry.register_pickup_point_provider(provider)
        assert registry.get_pickup_point_provider(PROVIDER_CDEK) is provider

    def test_register_and_get_document_provider(self):
        registry = ShippingProviderRegistry()
        provider = FakeDocumentProvider(code=PROVIDER_CDEK)
        registry.register_document_provider(provider)
        assert registry.get_document_provider(PROVIDER_CDEK) is provider


class TestRegistryLookupErrors:
    def test_get_missing_rate_provider_raises(self):
        registry = ShippingProviderRegistry()
        with pytest.raises(ProviderUnavailableError):
            registry.get_rate_provider("nonexistent")

    def test_get_missing_booking_provider_raises(self):
        registry = ShippingProviderRegistry()
        with pytest.raises(ProviderUnavailableError):
            registry.get_booking_provider("nonexistent")

    def test_get_missing_tracking_provider_raises(self):
        registry = ShippingProviderRegistry()
        with pytest.raises(ProviderUnavailableError):
            registry.get_tracking_provider("nonexistent")


class TestRegistryListing:
    def test_list_rate_providers(self):
        registry = ShippingProviderRegistry()
        p1 = FakeRateProvider(code=PROVIDER_CDEK)
        p2 = FakeRateProvider(code=PROVIDER_YANDEX_DELIVERY)
        registry.register_rate_provider(p1)
        registry.register_rate_provider(p2)
        assert len(registry.list_rate_providers()) == 2

    def test_list_tracking_poll_providers(self):
        registry = ShippingProviderRegistry()
        p1 = FakeTrackingPollProvider(code=PROVIDER_YANDEX_DELIVERY)
        registry.register_tracking_poll_provider(p1)
        result = registry.list_tracking_poll_providers()
        assert len(result) == 1
        assert result[0] is p1

    def test_registered_provider_codes(self):
        registry = ShippingProviderRegistry()
        registry.register_rate_provider(FakeRateProvider(code=PROVIDER_CDEK))
        registry.register_booking_provider(
            FakeBookingProvider(code=PROVIDER_YANDEX_DELIVERY)
        )
        codes = registry.registered_provider_codes
        assert codes == {PROVIDER_CDEK, PROVIDER_YANDEX_DELIVERY}


class TestWebhookAdapter:
    def test_has_webhook_adapter_false_when_empty(self):
        registry = ShippingProviderRegistry()
        assert registry.has_webhook_adapter(PROVIDER_CDEK) is False

    def test_get_missing_webhook_adapter_raises(self):
        registry = ShippingProviderRegistry()
        with pytest.raises(ProviderUnavailableError):
            registry.get_webhook_adapter(PROVIDER_CDEK)
