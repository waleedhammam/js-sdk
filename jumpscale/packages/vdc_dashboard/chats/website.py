from jumpscale.packages.vdc_dashboard.chats.publisher import Publisher
from jumpscale.sals.chatflows.chatflows import chatflow_step


class WebsiteDeploy(Publisher):
    EXAMPLE_URL = "https://github.com/threefoldfoundation/website_example"

    title = "Website"

    @chatflow_step(title="Configurations")
    def set_config(self):
        self._choose_flavor()

        form = self.new_form()
        title = form.string_ask("Title", required=True)
        url = form.string_ask("Repository URL", required=True, is_git_url=True)
        branch = form.string_ask("Branch", required=True)
        srcdir = form.string_ask("Source directory", required=False, default="html")
        msg = self.get_mdconfig_msg()
        form.ask(msg, md=True)
        self.chart_config.update(
            {
                "env.type": "www",
                "env.title": title.value,
                "env.url": url.value,
                "env.branch": branch.value,
                "env.srcdir": srcdir.value,
                "ingress.host": self.domain,
                "resources.limits.cpu": self.resources_limits["cpu"],
                "resources.limits.memory": self.resources_limits["memory"],
            }
        )


chat = WebsiteDeploy