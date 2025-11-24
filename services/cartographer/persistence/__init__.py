"""Persistence module for reconnaissance results."""
from .json_storage import save_reconnaissance_result, load_reconnaissance_result

__all__ = ['save_reconnaissance_result', 'load_reconnaissance_result']
