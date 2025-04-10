from registry_server import RegistryServer
from repository_server import RepositoryServer
from lifecycle_server import ServerLifeCycleServer

reg_server = RegistryServer("../registry-and-repository/registry")

reg_pid = reg_server.start()

repo_server = RepositoryServer("../registry-and-repository/repository")

repo_pid = repo_server.start()

life_server = ServerLifeCycleServer("../Server-Lifecycle-Management")

life_server_pid = life_server.start()
