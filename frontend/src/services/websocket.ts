/**
 * WebSocket service for real-time price updates
 */

interface TickerUpdate {
  symbol: string;
  price: number;
  priceChange: number;
  priceChangePercent: number;
  volume: number;
}

type SubscriptionCallback = (data: TickerUpdate) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private subscriptions = new Map<string, Set<SubscriptionCallback>>();
  private reconnectInterval: number = 5000;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private isConnecting = false;
  private maxReconnectAttempts = 10;
  private reconnectAttempts = 0;

  /**
   * Connect to Binance WebSocket stream
   */
  connect() {
    if (this.ws || this.isConnecting) {
      return;
    }

    this.isConnecting = true;

    try {
      // Connect to Binance WebSocket for all ticker data (메인넷)
      this.ws = new WebSocket('wss://stream.binance.com:9443/ws/!ticker@arr');

      this.ws.onopen = () => {
        console.log('✅ WebSocket connected to Binance');
        this.isConnecting = false;
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (Array.isArray(data)) {
            // Process ticker array data
            data.forEach((ticker: any) => {
              const update: TickerUpdate = {
                symbol: ticker.s,
                price: parseFloat(ticker.c),
                priceChange: parseFloat(ticker.p), // Price change in absolute value
                priceChangePercent: parseFloat(ticker.P), // Price change percentage
                volume: parseFloat(ticker.v)
              };

              this.notifySubscribers(ticker.s, update);
            });
          }
        } catch (error) {
          console.error('Error parsing WebSocket data:', error);
        }
      };

      this.ws.onclose = () => {
        console.log('❌ WebSocket connection closed');
        this.ws = null;
        this.isConnecting = false;
        this.scheduleReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.isConnecting = false;
      };
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      this.isConnecting = false;
      this.scheduleReconnect();
    }
  }

  /**
   * Disconnect WebSocket
   */
  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    this.subscriptions.clear();
    this.isConnecting = false;
    this.reconnectAttempts = 0;
  }

  /**
   * Subscribe to ticker updates for a specific symbol
   */
  subscribe(symbol: string, callback: SubscriptionCallback): () => void {
    if (!this.subscriptions.has(symbol)) {
      this.subscriptions.set(symbol, new Set());
    }

    this.subscriptions.get(symbol)!.add(callback);

    // Auto-connect if not connected
    if (!this.ws && !this.isConnecting) {
      this.connect();
    }

    // Return unsubscribe function
    return () => {
      const callbacks = this.subscriptions.get(symbol);
      if (callbacks) {
        callbacks.delete(callback);
        if (callbacks.size === 0) {
          this.subscriptions.delete(symbol);
        }
      }
    };
  }

  /**
   * Subscribe to multiple symbols at once
   */
  subscribeToSymbols(symbols: string[], callback: SubscriptionCallback): () => void {
    const unsubscribeFunctions = symbols.map(symbol =>
      this.subscribe(symbol, callback)
    );

    return () => {
      unsubscribeFunctions.forEach(unsubscribe => unsubscribe());
    };
  }

  /**
   * Check if WebSocket is connected
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Get current connection status
   */
  getConnectionStatus(): 'connected' | 'connecting' | 'disconnected' {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return 'connected';
    }
    if (this.isConnecting) {
      return 'connecting';
    }
    return 'disconnected';
  }

  private scheduleReconnect() {
    if (this.reconnectTimer || this.reconnectAttempts >= this.maxReconnectAttempts) {
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(this.reconnectInterval * this.reconnectAttempts, 30000);

    console.log(`🔄 Reconnecting WebSocket in ${delay}ms (attempt ${this.reconnectAttempts})`);

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  private notifySubscribers(symbol: string, data: TickerUpdate) {
    const callbacks = this.subscriptions.get(symbol);
    if (callbacks && callbacks.size > 0) {
      callbacks.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error('Error in subscription callback:', error);
        }
      });
    }
  }
}

// Export singleton instance
export const websocketService = new WebSocketService();
export type { TickerUpdate };