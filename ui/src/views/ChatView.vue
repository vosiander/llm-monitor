<template>
  <div class="chat-view">
    <div class="chat-header">
      <div class="level">
        <div class="level-left">
          <div class="level-item">
            <button class="button is-light" @click="$router.push('/')">
              <span class="icon">
                <v-icon name="fa-arrow-left" />
              </span>
              <span>Back</span>
            </button>
          </div>
          <div class="level-item">
            <h1 class="title is-4">Chat with {{ label }}</h1>
          </div>
        </div>
        <div class="level-right">
          <div class="level-item">
            <div class="field">
              <label class="label">Model</label>
              <div class="control">
                <div class="select" :class="{ 'is-loading': modelsLoading }">
                  <select v-model="selectedModel" :disabled="modelsLoading || chatLoading">
                    <option v-for="model in availableModels" :key="model" :value="model">
                      {{ model }}
                    </option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="chat-container">
      <div class="chat-messages" ref="chatMessages">
        <div v-if="chatHistory.length === 0" class="empty-state">
          <v-icon name="fa-comments" style="font-size: 4rem; color: #dbdbdb;" />
          <p class="has-text-grey mt-4">Start a conversation with {{ selectedModel || 'a model' }}</p>
        </div>
        <div v-for="(message, index) in chatHistory" :key="index"
             class="message-item"
             :class="{ 'user-message': message.role === 'user', 'assistant-message': message.role === 'assistant' }">
          <div class="message-bubble">
            <strong>{{ message.role === 'user' ? 'You' : 'Assistant' }}:</strong>
            <p>{{ message.content }}</p>
          </div>
        </div>
        <div v-if="chatLoading" class="message-item assistant-message">
          <div class="message-bubble">
            <v-icon name="fa-circle-notch" class="fa-spin" /> Thinking...
          </div>
        </div>
      </div>
    </div>

    <div class="chat-footer">
      <div class="field has-addons">
        <div class="control is-expanded">
          <input
            class="input is-large"
            type="text"
            v-model="chatInput"
            placeholder="Type your message..."
            @keydown.enter="sendMessage"
            :disabled="chatLoading || !selectedModel"
          >
        </div>
        <div class="control">
          <button
            class="button is-info is-large"
            @click="sendMessage"
            :disabled="!chatInput || chatLoading || !selectedModel"
            :class="{ 'is-loading': chatLoading }"
          >
            <span class="icon">
              <v-icon name="fa-paper-plane" />
            </span>
            <span>Send</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { inject } from 'vue';

export default {
  props: {
    label: {
      type: String,
      required: true
    }
  },
  data() {
    return {
      llmmonitor: inject('llmmonitor'),
      chatHistory: [],
      chatInput: '',
      chatLoading: false,
      availableModels: [],
      selectedModel: '',
      modelsLoading: false,
    };
  },
  mounted() {
    this.fetchModels();
  },
  methods: {
    async fetchModels() {
      this.modelsLoading = true;
      try {
        const response = await this.llmmonitor.axios.get(`/llmm/${this.label}/models`);
        this.availableModels = response.data.models || [];

        // Set first model as default if available
        if (this.availableModels.length > 0) {
          this.selectedModel = this.availableModels[0];
        }
      } catch (error) {
        console.error('Error fetching models:', error);
        this.availableModels = [];
      } finally {
        this.modelsLoading = false;
      }
    },
    async sendMessage() {
      if (!this.chatInput.trim()) return;

      const userMessage = { role: 'user', content: this.chatInput };
      this.chatHistory.push(userMessage);

      this.chatInput = '';
      this.chatLoading = true;

      try {
        const response = await fetch(
          `${this.llmmonitor.axios.defaults.baseURL}/llmm/${this.label}/chat`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              messages: this.chatHistory,
              stream: true,
              model: this.selectedModel,
            }),
          }
        );

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let assistantMessage = { role: 'assistant', content: '' };
        this.chatHistory.push(assistantMessage);

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n').filter(line => line.trim() && line.startsWith('data: '));

          for (const line of lines) {
            try {
              const jsonStr = line.replace('data: ', '');
              if (jsonStr === '[DONE]') continue;

              const data = JSON.parse(jsonStr);

              if (data.choices && data.choices[0]?.delta?.content) {
                assistantMessage.content += data.choices[0].delta.content;
                // Scroll to bottom
                this.$nextTick(() => {
                  if (this.$refs.chatMessages) {
                    this.$refs.chatMessages.scrollTop = this.$refs.chatMessages.scrollHeight;
                  }
                });
              }
            } catch (e) {
              console.error('Error parsing chat response:', e);
            }
          }
        }
      } catch (error) {
        console.error('Error sending message:', error);
        this.chatHistory.push({
          role: 'assistant',
          content: 'Error: Failed to get response from the model.',
        });
      } finally {
        this.chatLoading = false;
      }
    },
  },
};
</script>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 75vh;
  background-color: #f5f5f5;
}

.chat-header {
  background: white;
  padding: 1.5rem;
  border-bottom: 1px solid #dbdbdb;
  box-shadow: 0 2px 3px rgba(0,0,0,0.05);
}

.chat-header .title {
  margin: 0;
}

.chat-header .field {
  margin-bottom: 0;
}

.chat-header .label {
  font-size: 0.75rem;
  margin-bottom: 0.25rem;
}

.chat-container {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
  max-width: 1200px;
  width: 100%;
  margin: 0 auto;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  opacity: 0.5;
}

.message-item {
  margin-bottom: 1.5rem;
}

.user-message {
  display: flex;
  justify-content: flex-end;
}

.assistant-message {
  display: flex;
  justify-content: flex-start;
}

.message-bubble {
  max-width: 70%;
  padding: 1rem 1.25rem;
  border-radius: 1rem;
  background-color: white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.user-message .message-bubble {
  background-color: #3273dc;
  color: white;
}

.assistant-message .message-bubble {
  background-color: white;
  color: #363636;
}

.message-bubble strong {
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  opacity: 0.8;
}

.message-bubble p {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  line-height: 1.6;
}

.chat-footer {
  background: white;
  padding: 1.5rem;
  border-top: 1px solid #dbdbdb;
  box-shadow: 0 -2px 3px rgba(0,0,0,0.05);
}

.chat-footer .field {
  max-width: 1200px;
  margin: 0 auto;
}
</style>
