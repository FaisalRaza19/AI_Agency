type MessageCallback = (data: any) => void;
type StatusCallback = (status: 'connecting' | 'connected' | 'disconnected') => void;

class TelemetryWebSocketService {
  private ws: WebSocket | null = null;
  private url = 'ws://localhost:8000/api/v1/telemetry/ws';
  private reconnectTimeout = 1000;
  private maxReconnectTimeout = 30000;
  private isConnected = false;
  private messageListeners: Set<MessageCallback> = new Set();
  private statusListeners: Set<StatusCallback> = new Set();
  private pingIntervalId: any = null;

  constructor() {
    // Listen for logout events to disconnect immediately
    if (typeof window !== 'undefined') {
      window.addEventListener('auth_logout', () => this.disconnect());
    }
  }

  public connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const token = localStorage.getItem('uabe_access_token');
    if (!token) {
      this.updateStatus('disconnected');
      return;
    }

    this.updateStatus('connecting');
    const wsUrl = `${this.url}?token=${encodeURIComponent(token)}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.isConnected = true;
      this.reconnectTimeout = 1000; // reset backoff
      this.updateStatus('connected');
      this.startPingInterval();
    };

    this.ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === 'pong') return; // ignore keepalive echoes
        this.messageListeners.forEach((listener) => listener(payload));
      } catch (err) {
        console.error('Failed to parse WebSocket JSON payload:', err);
      }
    };

    this.ws.onclose = () => {
      this.isConnected = false;
      this.updateStatus('disconnected');
      this.stopPingInterval();
      this.ws = null;
      this.scheduleReconnect();
    };

    this.ws.onerror = (error) => {
      console.error('Telemetry WebSocket Error:', error);
      if (this.ws) {
        this.ws.close();
      }
    };
  }

  public disconnect(): void {
    this.stopPingInterval();
    if (this.ws) {
      this.ws.onclose = null; // prevent auto-reconnect triggers
      this.ws.close();
      this.ws = null;
    }
    this.isConnected = false;
    this.updateStatus('disconnected');
  }

  public onMessage(callback: MessageCallback): () => void {
    this.messageListeners.add(callback);
    return () => {
      this.messageListeners.delete(callback);
    };
  }

  public onStatusChange(callback: StatusCallback): () => void {
    this.statusListeners.add(callback);
    // Send immediate initial status
    callback(this.isConnected ? 'connected' : this.ws ? 'connecting' : 'disconnected');
    return () => {
      this.statusListeners.delete(callback);
    };
  }

  private updateStatus(status: 'connecting' | 'connected' | 'disconnected'): void {
    this.statusListeners.forEach((listener) => listener(status));
  }

  private scheduleReconnect(): void {
    setTimeout(() => {
      console.log(`Reconnecting to telemetry WebSocket stream... (Backoff: ${this.reconnectTimeout}ms)`);
      this.reconnectTimeout = Math.min(this.reconnectTimeout * 2, this.maxReconnectTimeout);
      this.connect();
    }, this.reconnectTimeout);
  }

  private startPingInterval(): void {
    this.stopPingInterval();
    this.pingIntervalId = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 15000); // 15 seconds heartbeat keepalive
  }

  private stopPingInterval(): void {
    if (this.pingIntervalId) {
      clearInterval(this.pingIntervalId);
      this.pingIntervalId = null;
    }
  }
}

export const telemetryWS = new TelemetryWebSocketService();
