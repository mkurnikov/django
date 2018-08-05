import subprocess
from concurrent.futures import ProcessPoolExecutor

from path import Path


def run_test_module_with_tracing(module) -> None:
    with open('tested_modules.txt', 'a') as tested_modules_file:
        base_args = ['monkeytype', '--config', 'generate_stubs:CONFIG', 'run', './runtests.py', '--parallel', '1',
                     '--keepdb']
        print('testing', module)

        command = base_args + [module]
        completed = subprocess.run(command,
                                   stdout=None,
                                   stderr=None,
                                   universal_newlines=True)
        if completed.returncode == 0:
            tested_modules_file.write(module + '\n')


if __name__ == '__main__':
    with open('tested_modules.txt', 'r') as tested_modules_file:
        old_tested_modules = set(tested_modules_file.read().split('\n'))

    modules_to_test = []
    for node in Path(__file__).parent.listdir():
        if node.isdir():
            node_basename = node.basename()
            if node_basename in old_tested_modules:
                continue

            modules_to_test.append(node_basename)

    pool = ProcessPoolExecutor(max_workers=3)
    for module_name, _ in zip(modules_to_test, pool.map(run_test_module_with_tracing, modules_to_test)):
        print(f'Finished testing {module_name}')