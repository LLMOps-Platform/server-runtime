from registry_server import RegistryServer
from repository_server import RepositoryServer

reg_server = RegistryServer("../registry-and-repository/registry")

reg_pid = reg_server.start()

repo_server = RepositoryServer("../registry-and-repository/repository")

repo_pid = repo_server.start()

