import os
import yaml
import asyncio
from typing import Dict, Optional
from pathlib import Path
from loguru import logger
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from crisisnet_common.enhanced_models import AgentConfig
from crisisnet_common.models import AgentRole


class ConfigFileHandler(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback
        self.last_modified = 0
    
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.yaml'):
            import time
            now = time.time()
            if now - self.last_modified > 1:
                self.last_modified = now
                self.callback(event.src_path)


class AgentConfigManager:
    def __init__(self, config_dir: str = "agents/configs"):
        self.config_dir = Path(config_dir)
        self.configs: Dict[AgentRole, AgentConfig] = {}
        self.observer: Optional[Observer] = None
        self._ensure_config_dir()
    
    def _ensure_config_dir(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def get_config_path(self, role: AgentRole) -> Path:
        return self.config_dir / f"{role.value}.yaml"
    
    def load_config(self, role: AgentRole) -> AgentConfig:
        config_path = self.get_config_path(role)
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    config = AgentConfig(**data)
                    self.configs[role] = config
                    logger.info(f"Loaded config for {role} from {config_path}")
                    return config
            except Exception as e:
                logger.error(f"Failed to load config for {role}: {e}")
        
        config = self._create_default_config(role)
        self.save_config(role, config)
        return config
    
    def _create_default_config(self, role: AgentRole) -> AgentConfig:
        defaults = {
            AgentRole.EOC: AgentConfig(
                decision_interval=5,
                llm_model="deepseek-chat"
            ),
            AgentRole.FIRE_RESCUE: AgentConfig(
                decision_interval=2,
                water_capacity=1000,
                llm_model="deepseek-chat"
            ),
            AgentRole.MEDICAL: AgentConfig(
                decision_interval=2,
                llm_model="deepseek-chat"
            ),
            AgentRole.LOGISTICS: AgentConfig(
                decision_interval=3,
                llm_model="deepseek-chat"
            ),
            AgentRole.PUBLIC_INFO: AgentConfig(
                decision_interval=4,
                llm_model="deepseek-chat"
            ),
        }
        return defaults.get(role, AgentConfig())
    
    def save_config(self, role: AgentRole, config: AgentConfig):
        config_path = self.get_config_path(role)
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config.model_dump(), f, allow_unicode=True, default_flow_style=False)
            self.configs[role] = config
            logger.info(f"Saved config for {role} to {config_path}")
        except Exception as e:
            logger.error(f"Failed to save config for {role}: {e}")
    
    def get_config(self, role: AgentRole) -> AgentConfig:
        if role not in self.configs:
            return self.load_config(role)
        return self.configs[role]
    
    def start_watching(self, reload_callback=None):
        if self.observer:
            return
        
        event_handler = ConfigFileHandler(
            lambda path: self._on_config_change(path, reload_callback)
        )
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.config_dir), recursive=False)
        self.observer.start()
        logger.info(f"Started watching config directory: {self.config_dir}")
    
    def stop_watching(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("Stopped watching config directory")
    
    def _on_config_change(self, path: str, callback=None):
        filename = os.path.basename(path)
        role_name = filename.replace('.yaml', '')
        try:
            role = AgentRole(role_name)
            self.load_config(role)
            if callback:
                callback(role)
            logger.info(f"Config reloaded for {role}")
        except ValueError:
            pass
