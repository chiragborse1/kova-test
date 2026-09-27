import pathlib
p = pathlib.Path("kova_cli/gateway_windows.py")
s = p.read_text(encoding="utf-8")
# The scheduled-task name also determines the .cmd/.vbs filenames written into
# the user's Startup folder, so the old name leaks onto their disk. Both the
# constant and the prose around it move together.
s = s.replace('_TASK_NAME_DEFAULT = "Kova_Gateway"', '_TASK_NAME_DEFAULT = "Kova_Gateway"', 1)
s = s.replace("Kova_Gateway.tmp", "Kova_Gateway.tmp")
s = s.replace("Kova_Gateway_alice", "Kova_Gateway_alice")
s = s.replace("Kova_Gateway", "Kova_Gateway")
p.write_text(s, encoding="utf-8")
print("task name -> Kova_Gateway")
