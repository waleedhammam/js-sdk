from jumpscale.sals.reservation_chatflow.deployer import DeploymentFailed
from jumpscale.loader import j

from jumpscale.sals.reservation_chatflow import deployer
from .size import *
from jumpscale.clients.explorer.models import ZDBMode, DiskType

import math
from .base_component import VDCBaseComponent


class VDCS3Deployer(VDCBaseComponent):
    def deploy_s3_minio_container(self, pool_id, ak, sk, ssh_key, scheduler, zdb_wids, vdc_uuid):
        zdb_configs = []
        self.vdc_deployer.info(f"deploying minio for zdbs: {zdb_wids}")
        for zid in zdb_wids:
            zdb_configs.append(deployer.get_zdb_url(zid, vdc_uuid, identity_name=self.identity.instance_name))
        self.vdc_deployer.info(f"zdb_configs: {zdb_configs}")

        network_view = deployer.get_network_view(self.vdc_name, identity_name=self.identity.instance_name)
        for node in scheduler.nodes_by_capacity(
            cru=MINIO_CPU, mru=MINIO_MEMORY / 1024, sru=MINIO_DISK / 1024, ip_version="IPv6"
        ):
            self.vdc_deployer.info(f"node {node.node_id} selected for minio")
            try:
                result = deployer.add_network_node(
                    self.vdc_name, node, pool_id, network_view, self.bot, self.identity.instance_name,
                )
                if result:
                    for wid in result["ids"]:
                        success = deployer.wait_workload(wid, self.bot, 5, identity_name=self.identity.instance_name)
                        if not success:
                            self.vdc_deployer.error(f"workload {wid} failed when adding node to network")
                            raise DeploymentFailed()
            except DeploymentFailed:
                self.vdc_deployer.error(f"failed to deploy minio network on node {node.node_id}.")
                continue

            network_view = network_view.copy()
            ip_address = network_view.get_free_ip(node)
            self.vdc_deployer.info(f"minio ip address {ip_address}")
            result = deployer.deploy_minio_containers(
                pool_id,
                self.vdc_name,
                [node.node_id],
                [ip_address],
                zdb_configs,
                ak,
                sk,
                ssh_key,
                MINIO_CPU,
                MINIO_MEMORY,
                S3_NO_DATA_NODES,
                S3_NO_PARITY_NODES,
                public_ipv6=True,
                disk_size=int(MINIO_DISK / 1024),
                bot=self.bot,
                identity_name=self.identity.instance_name,
                form_info={"chatflow": "minio"},
                name=self.vdc_name,
                solution_uuid=vdc_uuid,
            )
            wid = result[0]
            try:
                success = deployer.wait_workload(wid, self.bot, identity_name=self.identity.instance_name)
                if not success:
                    raise DeploymentFailed()
                self.vdc_deployer.info(f"minio container deployed successfully wid: {wid}")
                return wid
            except DeploymentFailed:
                self.vdc_deployer.error(f"failed to deploy minio container wid: {wid}")
                continue
        self.vdc_deployer.error("no nodes available to deploy minio container")

    def deploy_s3_zdb(self, pool_id, scheduler, storage_per_zdb, password, vdc_uuid):
        deployment_nodes = []
        wids = []
        for node in scheduler.nodes_by_capacity(sru=math.ceil(storage_per_zdb), ip_version="IPv6"):
            self.vdc_deployer.info(f"node {node.node_id} selected for zdb")
            deployment_nodes.append(node)
            if len(deployment_nodes) < S3_NO_DATA_NODES + S3_NO_PARITY_NODES - len(wids):
                continue
            self.vdc_deployer.info(f"staring zdb deployment on nodes {[node.node_id for node in deployment_nodes]}")
            result = []
            for node in deployment_nodes:
                self.vdc_deployer.info(f"deploying zdb on node: {node.node_id}")
                result.append(
                    deployer.deploy_zdb(
                        pool_id=pool_id,
                        node_id=node.node_id,
                        size=int(storage_per_zdb),
                        disk_type=DiskType.SSD,
                        mode=ZDBMode.Seq,
                        password=password,
                        form_info={"chatflow": "minio"},
                        name=self.vdc_name,
                        solution_uuid=vdc_uuid,
                        identity_name=self.identity.instance_name,
                    )
                )
            for wid in result:
                try:
                    success = deployer.wait_workload(
                        wid, bot=self.bot, expiry=3, identity_name=self.identity.instance_name
                    )
                    if not success:
                        raise DeploymentFailed()
                    wids.append(wid)
                    self.vdc_deployer.info(f"zdb deployed successfully wid: {wid}")
                except DeploymentFailed:
                    self.vdc_deployer.error(f"failed to deploy zdb wid: {wid}")
                    continue
            if len(wids) == S3_NO_DATA_NODES + S3_NO_PARITY_NODES:
                self.vdc_deployer.info("all zdbs deployed successfully")
                return wids
            deployment_nodes = []
        self.vdc_deployer.error("no nodes available to deploy zdb")
