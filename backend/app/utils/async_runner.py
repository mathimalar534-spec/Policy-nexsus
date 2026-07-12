import logging
from fastapi import BackgroundTasks
from app.config.config import settings

logger = logging.getLogger(__name__)

def trigger_background_job(background_tasks: BackgroundTasks, task_func, *args, **kwargs):
    """
    Attempts to trigger a Celery job. If Celery or Redis is unavailable or disabled,
    it falls back to FastAPI's BackgroundTasks to execute the logic in a separate thread,
    preventing application blockages during local testing.
    """
    use_celery = False
    
    # Try calling the celery delay method
    try:
        if hasattr(task_func, "delay"):
            # Check Redis connection if possible
            import redis
            r = redis.from_url(settings.REDIS_URL, socket_timeout=1.0)
            r.ping()
            
            # If ping succeeded, trigger Celery task
            task_func.delay(*args, **kwargs)
            logger.info(f"Triggered task {task_func.__name__} asynchronously via Celery.")
            use_celery = True
    except Exception as e:
        logger.warning(f"Celery broker unreachable or connection failed ({str(e)}). Falling back to FastAPI BackgroundTasks.")
        
    if not use_celery:
        # Fall back to FastAPI background runner
        # Since Celery wraps functions, the original function is usually available as task_func.run or task_func
        func_to_run = task_func
        if hasattr(task_func, "run"):
            func_to_run = task_func.run
            
        background_tasks.add_task(func_to_run, *args, **kwargs)
        logger.info(f"Triggered task {func_to_run.__name__} via FastAPI BackgroundTasks thread.")
