import os
import time
from typing import Dict, Any, List, Optional
import pyTigerGraph as tg
from src.core.config import settings

class TigerGraphClient:
    """
    Manages connection and query execution to TigerGraph (Savanna or Community Edition).
    """
    def __init__(
        self,
        host: Optional[str] = None,
        graphname: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        secret: Optional[str] = None,
        api_token: Optional[str] = None,
    ):
        self.host = host or settings.tg_host
        self.graphname = graphname or settings.tg_graph
        self.username = username or settings.tg_username
        self.password = password or settings.tg_password
        self.secret = secret or settings.tg_secret
        self.api_token = api_token or settings.tg_api_token
        self._conn: Optional[tg.TigerGraphConnection] = None

    def get_connection(self) -> tg.TigerGraphConnection:
        if self._conn is None:
            is_cloud = bool("tgcloud.io" in self.host.lower() or "tgcloud" in self.host.lower())
            self._conn = tg.TigerGraphConnection(
                host=self.host,
                graphname=self.graphname,
                username=self.username,
                password=self.password,
                gsqlSecret=self.secret if self.secret else "",
                apiToken=self.api_token if self.api_token else "",
                tgCloud=is_cloud,
            )
            if self.secret and not self.api_token:
                try:
                    self.api_token = self._conn.getToken(self.secret)
                except Exception:
                    pass
        return self._conn

    def is_connected(self) -> bool:
        """Returns True if the connection to TigerGraph is alive."""
        return bool(self.ping().get("connected", False))

    def ping(self) -> Dict[str, Any]:
        """Tests connectivity to TigerGraph server."""
        try:
            conn = self.get_connection()
            status = conn.ping()
            return {"connected": True, "status": status}
        except Exception as e:
            return {"connected": False, "error": str(e)}

    def gsql(self, query: str) -> str:
        """Executes raw GSQL script/command."""
        conn = self.get_connection()
        return conn.gsql(query)

    def run_installed_query(self, query_name: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Executes pre-installed GSQL query."""
        conn = self.get_connection()
        return conn.runInstalledQuery(query_name, params=params or {})

    def get_vertex_count(self, vertex_type: str = "*") -> Any:
        conn = self.get_connection()
        return conn.getVertexCount(vertex_type)

    def get_edge_count(self, edge_type: str = "*") -> Any:
        conn = self.get_connection()
        return conn.getEdgeCount(edge_type)

    def upsert_vertex(self, vertex_type: str, vertex_id: str, attributes: Dict[str, Any]) -> Any:
        conn = self.get_connection()
        return conn.upsertVertex(vertex_type, vertex_id, attributes)

    def upsert_vertices(self, vertex_type: str, vertices_data: Dict[str, Dict[str, Any]]) -> Any:
        conn = self.get_connection()
        return conn.upsertVertices(vertex_type, vertices_data)

    def upsert_edge(
        self,
        source_vertex_type: str,
        source_vertex_id: str,
        edge_type: str,
        target_vertex_type: str,
        target_vertex_id: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Any:
        conn = self.get_connection()
        return conn.upsertEdge(
            source_vertex_type,
            source_vertex_id,
            edge_type,
            target_vertex_type,
            target_vertex_id,
            attributes=attributes or {},
        )
