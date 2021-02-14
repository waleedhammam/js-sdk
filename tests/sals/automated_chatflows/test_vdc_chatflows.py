import gevent
from tests.base_tests import BaseTests
import pytest
from jumpscale.loader import j
from solutions_automation.vdc import deployer
from tests.sals.vdc.vdc_base import VDCBase
from parameterized import parameterized_class


@parameterized_class(("flavor"), [("silver",), ("gold",), ("platinum",), ("diamond",)])
@pytest.mark.integration
class VDCChatflows(VDCBase):
    flavor = "silver"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._import_wallet(wallet_name="vdc_init")
        cls._import_wallet(wallet_name="grace_period")
        cls.config_vdc = j.core.config.get("VDC_INITIALIZATION_WALLET")
        j.core.config.set("VDC_INITIALIZATION_WALLET", "vdc_init")

    @classmethod
    def tearDownClass(cls):
        if cls.config_vdc:
            j.core.config.set("VDC_INITIALIZATION_WALLET", cls.config_vdc)

    def setUp(self):
        self.vdc = None
        super().setUp()

    def tearDown(self):

        self.info("Delete a VDC")
        if self.vdc:
            j.sals.vdc.delete(self.vdc.vdc.instance_name)

            wallet = j.clients.stellar.get("demos_wallet")
            self.vdc.vdc.provision_wallet.merge_into_account(wallet.address)
            self.vdc.vdc.prepaid_wallet.merge_into_account(wallet.address)

        super().tearDown()

    def test_01_deploy_vdc(self):
        """Test case for deploying a VDC.

        **Test Scenario**

        - Deploy a VDC.
        - Check that VDC is reachable.
        - Delete a VDC
        """

        self.info("Deploy a VDC")
        vdc_name = self.random_name().lower()
        password = self.random_string()
        self.vdc = deployer.deploy_vdc(vdc_name, password, self.flavor.upper())

        self.info("Check that VDC is reachable")
        request = j.tools.http.get(f"http://{vdc.vdc.threebot.domain}", timeout=60)
        self.assertEqual(request.status_code, 200)