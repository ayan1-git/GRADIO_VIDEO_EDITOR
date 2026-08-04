import os
import subprocess
from typing import List


def execute_render(commands: List[str],
                   checkpoint_dir: str = "/kaggle/working/.checkpoints"):
    """
    Execute render commands with checkpointing.

    Args:
        commands: List of shell commands from build_render_commands()
        checkpoint_dir: Directory to store checkpoint files
    """
    os.makedirs(checkpoint_dir, exist_ok=True)

    for i, cmd in enumerate(commands):
        checkpoint_file = os.path.join(checkpoint_dir, f"step_{i:04d}.done")

        if os.path.exists(checkpoint_file):
            print(f"[{i+1}/{len(commands)}] Already completed, skipping")
            continue

        print(f"[{i+1}/{len(commands)}] Executing: {cmd[:100]}...")

        try:
            result = subprocess.run(
                cmd, shell=True, check=True,
                capture_output=True, text=True
            )

            open(checkpoint_file, 'w').close()
            print(f"[{i+1}/{len(commands)}] Success")

        except subprocess.CalledProcessError as e:
            print(f"[{i+1}/{len(commands)}] Failed with exit code {e.returncode}")
            print(f"Error output:\n{e.stderr}")

            error_log = os.path.join(checkpoint_dir, f"step_{i:04d}.error")
            with open(error_log, 'w') as f:
                f.write(f"Command:\n{cmd}\n\n")
                f.write(f"Exit code: {e.returncode}\n\n")
                f.write(f"Stderr:\n{e.stderr}\n")

            raise RuntimeError(f"Render failed at step {i+1}. See {error_log}")

    print("All render steps completed successfully")
