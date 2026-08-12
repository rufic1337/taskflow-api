import os

# Run Celery tasks synchronously during the test suite so we don't need a
# broker or worker running, and so task side-effects (e.g. Notification rows,
# "sent" emails) are visible immediately within the same test.
os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "True")
