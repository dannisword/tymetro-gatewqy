import { ref, onUnmounted } from 'vue';
import { defineStore, storeToRefs } from 'pinia';
import mqtt from 'mqtt';

// 🚀 用於匹配 MQTT 主題通配符 (+ 和 #) 的輔助函數
function matchTopic(pattern: string, topic: string): boolean {
  const patternParts = pattern.split('/');
  const topicParts = topic.split('/');

  for (let i = 0; i < patternParts.length; i++) {
    const pPart = patternParts[i];
    if (pPart === '#') {
      return true;
    }
    const tPart = topicParts[i];
    if (tPart === undefined) {
      return false;
    }
    if (pPart !== '+' && pPart !== tPart) {
      return false;
    }
  }
  return topicParts.length === patternParts.length;
}

// 1. 定義全域唯一的 Pinia Store 來管理連線與狀態
export const useMQTTStore = defineStore('useMQTT', () => {
  const client = ref<mqtt.MqttClient | null>(null);
  const isConnected = ref(false);

  // 用來註冊多個訂閱者的 Callback 列表：topic -> Set of callbacks
  const callbacks = new Map<string, Set<(topic: string, message: any) => void>>();

  const connect = (brokerUrl: string = 'ws://220.133.144.72:9001') => {
    // 若已建立連線，則不重複執行
    if (client.value && client.value.connected) {
      console.log('[useMQTT] Client already connected.');
      return;
    }
    if (client.value) {
      console.log('[useMQTT] Client connection in progress...');
      return;
    }

    console.log('[useMQTT] Connecting to MQTT broker:', brokerUrl);
    client.value = mqtt.connect(brokerUrl, {
      connectTimeout: 10000,
      keepalive: 60,
      clean: true,
      clientId: 'tymetro_air_' + Math.random().toString(16).substring(2, 8),
    });

    client.value.on('connect', () => {
      console.log('[useMQTT] Connected to MQTT broker successfully.');
      isConnected.value = true;

      // 連線成功後，統一向 Broker 訂閱所有目前已登記的 Topic Pattern
      for (const topic of callbacks.keys()) {
        console.log(`[useMQTT] Re-subscribing to registered topic on connect: "${topic}"`);
        client.value?.subscribe(topic, (err) => {
          if (err) {
            console.error(`[useMQTT] Re-subscribe failed for "${topic}":`, err);
          } else {
            console.log(`[useMQTT] Re-subscribed successfully to: "${topic}"`);
          }
        });
      }
    });

    client.value.on('error', (err) => {
      console.error('[useMQTT] MQTT connection error:', err);
    });

    client.value.on('close', () => {
      console.log('[useMQTT] MQTT connection closed');
      isConnected.value = false;
    });

    // 註冊全域單一的 message 接收點，分發訊息給各個註冊的 callback（支援通配符匹配）
    client.value.on('message', (t, message) => {
      const messageStr = message.toString();
      console.log(`[useMQTT] Received message on topic: "${t}" | Payload:`, messageStr.substring(0, 150));

      let matchedAny = false;
      callbacks.forEach((topicCallbacks, pattern) => {
        const isMatched = matchTopic(pattern, t);
        if (isMatched) {
          matchedAny = true;
          // console.log(`[useMQTT] Topic "${t}" matched registered pattern "${pattern}". Dispatching callbacks...`);
          let payload: any;
          try {
            payload = JSON.parse(messageStr);
          } catch (e) {
            payload = messageStr;
          }
          topicCallbacks.forEach(cb => {
            try {
              cb(t, payload);
            } catch (e) {
              console.error('[useMQTT] Error in callback execution:', e);
            }
          });
        }
      });

      if (!matchedAny) {
        console.warn(`[useMQTT] Received message on "${t}" but it did not match any active patterns:`, Array.from(callbacks.keys()));
      }
    });
  };

  // 用於延遲退訂的計時器對照表
  const pendingUnsubscribes = new Map<string, any>();

  const subscribeTopic = (topic: string, callback: (topic: string, message: any) => void) => {
    // 若該主題有 pending 的退訂，則將其取消
    if (pendingUnsubscribes.has(topic)) {
      clearTimeout(pendingUnsubscribes.get(topic));
      pendingUnsubscribes.delete(topic);
      console.log(`[useMQTT] Cancelled pending unsubscribe for: "${topic}"`);
    }

    let topicCallbacks = callbacks.get(topic);
    const isNewTopic = !topicCallbacks;

    if (!topicCallbacks) {
      topicCallbacks = new Set();
      callbacks.set(topic, topicCallbacks);
    }

    topicCallbacks.add(callback);
    console.log(`[useMQTT] Callback added to pattern "${topic}". Current listener count: ${topicCallbacks.size}`);

    // 僅在「新主題」且「已建立連線」的情況下向 Broker 發送 subscribe 請求
    // 若未連線，則會在連線成功的 'connect' 事件中自動發送訂閱
    if (isNewTopic) {
      if (client.value && isConnected.value) {
        console.log(`[useMQTT] Client is connected. Sending subscribe request to Broker for: "${topic}"`);
        client.value.subscribe(topic, (err) => {
          if (err) {
            console.error(`[useMQTT] Subscription failed on Broker for "${topic}":`, err);
          } else {
            console.log(`[useMQTT] Subscription confirmed by Broker for: "${topic}"`);
          }
        });
      } else {
        console.log(`[useMQTT] Client not connected yet. Subscription for "${topic}" queued in registry.`);
      }
    }
  };

  const unsubscribeTopic = (topic: string, callback: (topic: string, message: any) => void) => {
    const topicCallbacks = callbacks.get(topic);
    if (topicCallbacks) {
      topicCallbacks.delete(callback);
      console.log(`[useMQTT] Callback removed from pattern "${topic}". Remaining listeners: ${topicCallbacks.size}`);

      // 若該 Topic 沒有任何人監聽，延遲 500ms 向 Broker 發送退訂，避免組件切換（例如切換車廂）時的退訂與重新訂閱競爭
      if (topicCallbacks.size === 0) {
        callbacks.delete(topic);

        if (pendingUnsubscribes.has(topic)) {
          clearTimeout(pendingUnsubscribes.get(topic));
        }

        const timer = setTimeout(() => {
          pendingUnsubscribes.delete(topic);
          if (client.value && isConnected.value) {
            console.log(`[useMQTT] No more listeners for "${topic}" after delay. Sending unsubscribe to Broker.`);
            client.value.unsubscribe(topic, (err) => {
              if (err) {
                console.error(`[useMQTT] Unsubscribe failed for "${topic}":`, err);
              } else {
                console.log(`[useMQTT] Unsubscribed confirmed by Broker for: "${topic}"`);
              }
            });
          }
        }, 500);

        pendingUnsubscribes.set(topic, timer);
      }
    }
  };

  const publish = (topic: string, message: any, options?: mqtt.IClientPublishOptions) => {
    if (!client.value) {
      console.error('[useMQTT] MQTT client not initialized');
      return;
    }

    const payload = typeof message === 'string' ? message : JSON.stringify(message);
    client.value.publish(topic, payload, options || {}, (err) => {
      if (err) {
        console.error(`[useMQTT] Failed to publish to ${topic}:`, err);
      }
    });
  };

  const disconnect = () => {
    if (client.value) {
      client.value.end();
      client.value = null;
      isConnected.value = false;
      callbacks.clear();
      console.log('[useMQTT] Manually disconnected and cleared registry.');
    }
  };

  // 🔍 診斷定時器：每 5 秒輸出目前 MQTT 連線與訂閱狀態
  // if (import.meta.env.DEV == false) {
  //   setInterval(() => {
  //     console.log('[useMQTT Diagnostic]', {
  //       storeIsConnected: isConnected.value,
  //       clientConnected: client.value?.connected,
  //       registeredPatterns: Array.from(callbacks.keys()),
  //       clientExists: !!client.value
  //     });
  //   }, 5000);
  // }

  return {
    client,
    isConnected,
    connect,
    subscribeTopic,
    unsubscribeTopic,
    publish,
    disconnect
  };
});

// 2. 提供與原 useMQTT 語法完全相容的 Composable 封裝
export function useMQTT() {
  const store = useMQTTStore();
  const { isConnected } = storeToRefs(store);

  // 記錄此組件實例註冊的訂閱，用於卸載時自動清理
  const localSubscriptions: { topic: string; callback: (topic: string, message: any) => void }[] = [];

  const subscribe = (topic: string, callback: (topic: string, message: any) => void) => {
    store.subscribeTopic(topic, callback);
    localSubscriptions.push({ topic, callback });
  };

  onUnmounted(() => {
    localSubscriptions.forEach(({ topic, callback }) => {
      store.unsubscribeTopic(topic, callback);
    });
  });

  return {
    isConnected,
    connect: store.connect,
    subscribe,
    publish: store.publish,
    disconnect: store.disconnect
  };
}
