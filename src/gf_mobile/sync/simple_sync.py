"""
SimpleSyncService

Servicio simplificado para sincronización bidireccional con Firestore.
Combina push y pull en una sola operación.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from gf_mobile.sync.protocol import SyncProtocol
from gf_mobile.core.exceptions import SyncError


@dataclass
class SyncResult:
    """Resultado de una operación de sincronización"""
    pushed: int  # Eventos enviados a Firestore
    pulled: int  # Eventos recibidos de Firestore
    success: bool
    error: Optional[str] = None


class SimpleSyncService:
    """
    Servicio simplificado de sincronización.
    
    Combina push y pull en una sola operación para facilitar
    la sincronización bidireccional.
    """

    def __init__(self, sync_protocol: SyncProtocol):
        """
        Inicializa el servicio.
        
        Args:
            sync_protocol: Instancia de SyncProtocol configurada
        """
        self.sync_protocol = sync_protocol

    async def sync_now(
        self,
        push_limit: int = 100,
        pull_limit: int = 50,
    ) -> SyncResult:
        """
        Ejecuta sincronización bidireccional completa.
        
        1. Push: Envía cambios locales pendientes a Firestore
        2. Pull: Descarga y aplica eventos remotos
        
        Args:
            push_limit: Máximo de eventos a enviar
            pull_limit: Máximo de eventos a recibir por página
            
        Returns:
            SyncResult con estadísticas y estado
        """
        pushed = 0
        pulled = 0
        error = None

        try:
            # Push: Enviar cambios locales
            pushed = await self.sync_protocol.push_outbox(limit=push_limit)
            
            # Pull: Recibir y aplicar cambios remotos
            pulled = await self.sync_protocol.pull_and_apply(page_size=pull_limit)
            
            return SyncResult(
                pushed=pushed,
                pulled=pulled,
                success=True,
            )

        except SyncError as e:
            error = str(e)
            return SyncResult(
                pushed=pushed,
                pulled=pulled,
                success=False,
                error=error,
            )
        except Exception as e:
            error = f"Error inesperado: {str(e)}"
            return SyncResult(
                pushed=pushed,
                pulled=pulled,
                success=False,
                error=error,
            )

    def sync_now_blocking(
        self,
        push_limit: int = 100,
        pull_limit: int = 50,
    ) -> SyncResult:
        """
        Versión bloqueante de sync_now para uso en threads.
        
        Args:
            push_limit: Máximo de eventos a enviar
            pull_limit: Máximo de eventos a recibir
            
        Returns:
            SyncResult con estadísticas y estado
        """
        return asyncio.run(self.sync_now(push_limit, pull_limit))

    async def push_only(self, limit: int = 100) -> SyncResult:
        """
        Solo envía cambios locales a Firestore.
        
        Args:
            limit: Máximo de eventos a enviar
            
        Returns:
            SyncResult con estadísticas
        """
        try:
            pushed = await self.sync_protocol.push_outbox(limit=limit)
            return SyncResult(
                pushed=pushed,
                pulled=0,
                success=True,
            )
        except SyncError as e:
            return SyncResult(
                pushed=0,
                pulled=0,
                success=False,
                error=str(e),
            )

    async def pull_only(self, limit: int = 50) -> SyncResult:
        """
        Solo descarga y aplica cambios remotos.
        
        Args:
            limit: Máximo de eventos a recibir
            
        Returns:
            SyncResult con estadísticas
        """
        try:
            pulled = await self.sync_protocol.pull_and_apply(page_size=limit)
            return SyncResult(
                pushed=0,
                pulled=pulled,
                success=True,
            )
        except SyncError as e:
            return SyncResult(
                pushed=0,
                pulled=0,
                success=False,
                error=str(e),
            )

    def get_last_sync_info(self) -> dict:
        """
        Obtiene información sobre la última sincronización.
        
        Returns:
            Dict con timestamps de última sincronización
        """
        return {
            "last_pull": self.sync_protocol.get_last_pull_timestamp(),
        }
