# Handles connection and configuration of box after boot up
# Note this is largely adapted from:
# - http://docs.ansible.com/ansible/dev_guide/developing_api.html#python-api-2-0
# - https://serversforhackers.com/running-ansible-programmatically

import json
from pprint import pprint
from collections import namedtuple
from tempfile import NamedTemporaryFile

import ansible

ansible.DEFAULT_VERBOSITY = 4

from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.inventory import Inventory
from ansible.parsing.dataloader import DataLoader
from ansible.playbook import Playbook
from ansible.playbook.play import Play
from ansible.plugins.callback import CallbackBase
from ansible.vars import VariableManager


class ResultCallback(CallbackBase):

    def runner_on_ok(self, host, result):
        """Print a json representation of the result
        """
        print('Success')
        pprint(result)

    def runner_on_unreachable(self, host, res):
        print('Unreachable', host) 
        pprint(res)

    def runner_on_failed(self, host, result, ignore_errors=False):
        print('Failed')
        print(host, result)

    def runner_on_async_failed(self, host, res, jid):
        print(host, 'ASYNC_FAILED', res)

    def playbook_on_import_for_host(self, host, imported_file):
        print(host, 'IMPORTED', imported_file)

    def playbook_on_not_import_for_host(self, host, missing_file):
        print(host, 'NOTIMPORTED', missing_file)


Options = namedtuple('Options', [
            'connection',
            'verbosity',
            'module_path',
            'forks',
            'become',
            'become_method',
            'become_user', 
            'user',
            'listhosts', 
            'listtasks',
            'listtags',
            'syntax',
            'check'
          ])


def run_play(ip_addr):
    options = Options(module_path='./env/lib/python3.5/site-packages/ansible/modules/',
                      verbosity=4,
                      forks=100,
                      connection='ssh',
                      become=None,
                      become_method=None,
                      become_user=None,
                      user='ubuntu',
                      listhosts='',
                      listtasks='',
                      listtags='',
                      syntax=False,
                      check=False)

    variable_manager = VariableManager()
    loader = DataLoader()
    results_callback = ResultCallback()

    host_str = '\n%s ansible_python_interpreter=/usr/bin/python3\n' % ip_addr

    hosts = NamedTemporaryFile()
    hosts.write(bytes(host_str, 'ASCII'))
    hosts.flush()

    inventory = Inventory(loader=loader, variable_manager=variable_manager, host_list=hosts.name)
    variable_manager.set_inventory(inventory)

    tasks = loader.load_from_file('playbooks/gl_install_task.yml')

    play_source =  dict(
        name = "manual play exec",
        user = "ubuntu",
        hosts = ip_addr,
        gather_facts = 'no',
        tasks = tasks
    )

    play = Play().load(play_source, variable_manager=variable_manager, loader=loader)

    tqm = None
    try:
        print('Launching task queue')
        tqm = TaskQueueManager(
            inventory=inventory,
            variable_manager=variable_manager,
            loader=loader,
            options=options,
            passwords=None,
            stdout_callback=results_callback,
        )
        result = tqm.run(play)
        print('Saw result:', result)
    except Exception as e:
        print('Failed %s' % e)
    finally:
        if tqm is not None:
            tqm.cleanup()
        hosts.close()


if __name__ == '__main__':
    run_play('34.250.10.80')
