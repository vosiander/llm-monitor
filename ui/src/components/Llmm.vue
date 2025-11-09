<template>
  <div class="llm-monitor">
    <div class="header-section">
      <div class="level">
        <div class="level-left">
          <div class="level-item">
            <h1 class="title">
              LLM Monitor
            </h1>
          </div>
        </div>
        <div class="level-right">
          <div class="level-item">
            <div class="refresh-controls">
              <span v-if="refreshState.loading" class="loading-spinner">
                <v-icon name="fa-circle-notch" class="fa-spin" />
              </span>
              <div class="select is-small">
                <select v-model="refreshInterval" @change="updateRefreshInterval">
                  <option :value="5000">5s</option>
                  <option :value="10000">10s</option>
                  <option :value="15000">15s</option>
                </select>
              </div>
            </div>
          </div>
        </div>
      </div>
      <p class="subtitle">
        Updated in real time. Click on a system to view information.
      </p>
    </div>

    <div class="table-container" v-if="filteredEndpoints">
      <div class="search-container">
        <div class="search-field">
          <span class="search-icon">
            <v-icon name="fa-search" />
          </span>
          <input
            type="text"
            v-model="searchQuery"
            placeholder="Search"
            ref="searchInput"
            @keydown.esc="clearSearch"
          >
          <span class="shortcut-hint">⌘ K</span>
        </div>
      </div>
      <table class="table is-fullwidth">
        <thead>
          <tr>
            <th>
              <span class="icon-text">
                <span class="icon"><v-icon name="fa-server" /></span>
                <span>System</span>
              </span>
            </th>
            <th>
              <span class="icon-text">
                <span class="icon"><v-icon name="fa-network-wired" /></span>
                <span>IP Address</span>
              </span>
            </th>
            <th>
              <span class="icon-text">
                <span class="icon"><v-icon name="fa-microchip" /></span>
                <span>VRAM Bar</span>
              </span>
            </th>
            <th>
              <span class="icon-text">
                <span class="icon"><v-icon name="fa-percent" /></span>
                <span>VRAM %</span>
              </span>
            </th>
            <th>
              <span class="icon-text">
                <span class="icon"><v-icon name="fa-clock" /></span>
                <span>Expires At</span>
              </span>
            </th>
            <th>Models</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(plugin, label) in filteredEndpoints" :key="label">
            <td>
              <div class="system-name">
                <span class="status-dot" :class="{ 'is-online': plugin.is_online }"></span>
                {{ label }}
              </div>
            </td>
            <td>
              <div class="ip-address">
                {{ plugin.ip || 'N/A' }}
              </div>
            </td>
            <td>
              <div class="vram-usage">
                <progress
                  class="progress"
                  :class="getVramClass(plugin.models)"
                  :value="calculateVramUsage(plugin.models)"
                  max="100">
                </progress>
              </div>
            </td>
            <td>
              <span class="vram-text">{{ formatVramUsage(plugin.models) }}</span>
            </td>
            <td>
              <span class="time-remaining">{{ formatTimeRemaining(plugin.models) }}</span>
            </td>
            <td>
              <div class="models-list">
                {{ plugin.models ? plugin.models.map(m => m.name).join(', ') : 'No models' }}
              </div>
            </td>
            <td>
              <div class="buttons are-small">
                <button class="button is-link is-light" @click="openListModal(label)">
                  <span class="icon">
                    <v-icon name="fa-list" />
                  </span>
                  <span>List</span>
                </button>
                <button class="button is-primary is-light" @click="openPullModal(label)">
                  <span class="icon">
                    <v-icon name="fa-download" />
                  </span>
                  <span>Pull</span>
                </button>
                <button class="button is-info is-light" @click="openChatModal(label)">
                  <span class="icon">
                    <v-icon name="fa-comments" />
                  </span>
                  <span>Run</span>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="loading-container">
      <div class="loading-content">
        <v-icon name="fa-circle-notch" class="fa-spin loading-icon" />
        <h2 class="loading-title">Connecting to LLM Systems</h2>
        <p class="loading-text">Please wait while we establish connections...</p>
      </div>
    </div>

    <!-- Pull Modal -->
    <div v-if="pullModalActive" class="modal is-active">
      <div class="modal-background" @click="pullModalActive = false"></div>
      <div class="modal-card">
        <header class="modal-card-head">
          <p class="modal-card-title">Pull Model - {{ selectedHost }}</p>
          <button class="delete" aria-label="close" @click="pullModalActive = false"></button>
        </header>
        <section class="modal-card-body">
          <div class="field">
            <label class="label">Model Name</label>
            <div class="control">
              <input
                class="input"
                type="text"
                v-model="pullModelName"
                placeholder="e.g., gemma2:2b, llama3:8b"
                :disabled="pullInProgress"
              >
            </div>
            <p class="help">Enter the model name and tag to pull from Ollama</p>
          </div>

          <div v-if="pullInProgress" class="progress-section">
            <progress class="progress is-primary" :value="pullProgress" max="100">
              {{ pullProgress }}%
            </progress>
            <p class="pull-status">{{ pullStatus }}</p>
          </div>

          <div v-if="pullError" class="notification is-danger">
            {{ pullError }}
          </div>

          <div v-if="pullComplete" class="notification is-success">
            Model pulled successfully!
          </div>
        </section>
        <footer class="modal-card-foot">
          <button
            class="button is-primary"
            @click="startPull"
            :disabled="!pullModelName || pullInProgress"
            :class="{ 'is-loading': pullInProgress }"
          >
            Pull Model
          </button>
          <button class="button" @click="closePullModal">Close</button>
        </footer>
      </div>
    </div>

    <!-- Chat Modal -->
    <div v-if="chatModalActive" class="modal is-active">
      <div class="modal-background" @click="chatModalActive = false"></div>
      <div class="modal-card chat-modal">
        <header class="modal-card-head">
          <p class="modal-card-title">Chat with {{ selectedHost }}</p>
          <div class="modal-header-actions">
            <button
              class="button is-small is-light"
              @click="openFullscreenChat"
              title="Open in fullscreen"
            >
              <span class="icon">
                <v-icon name="fa-expand" />
              </span>
            </button>
            <button class="delete" aria-label="close" @click="chatModalActive = false"></button>
          </div>
        </header>
        <section class="modal-card-body chat-body">
          <div class="model-selector-container">
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
          <div class="chat-messages" ref="chatMessages">
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
        </section>
        <footer class="modal-card-foot chat-footer">
          <div class="field has-addons" style="flex: 1;">
            <div class="control" style="flex: 1;">
              <input
                class="input"
                type="text"
                v-model="chatInput"
                placeholder="Type your message..."
                @keydown.enter="sendMessage"
                :disabled="chatLoading"
              >
            </div>
            <div class="control">
              <button
                class="button is-info"
                @click="sendMessage"
                :disabled="!chatInput || chatLoading"
                :class="{ 'is-loading': chatLoading }"
              >
                Send
              </button>
            </div>
          </div>
        </footer>
      </div>
    </div>

    <!-- List Models Modal -->
    <div v-if="listModalActive" class="modal is-active">
      <div class="modal-background" @click="listModalActive = false"></div>
      <div class="modal-card">
        <header class="modal-card-head">
          <p class="modal-card-title">Models on {{ selectedHost }}</p>
          <button class="delete" aria-label="close" @click="listModalActive = false"></button>
        </header>
        <section class="modal-card-body">
          <div v-if="listModelsLoading" class="has-text-centered">
            <v-icon name="fa-circle-notch" class="fa-spin" style="font-size: 2rem; color: #7957d5;" />
            <p class="mt-3">Loading models...</p>
          </div>
          <div v-else-if="listModels.length === 0" class="has-text-centered">
            <p class="has-text-grey">No models available on this host</p>
          </div>
          <div v-else class="models-list-container">
            <p class="has-text-weight-semibold mb-3">Available Models:</p>
            <ul class="model-items">
              <li v-for="model in listModels" :key="model" class="model-item">
                <div class="model-item-content">
                  <span class="icon has-text-link">
                    <v-icon name="fa-cube" />
                  </span>
                  <span class="model-name">{{ model }}</span>
                </div>
                <button
                  class="button is-danger is-small is-light"
                  @click="confirmDeleteModel(model)"
                  :disabled="deleteInProgress"
                  title="Delete model"
                >
                  <span class="icon">
                    <v-icon name="fa-trash" />
                  </span>
                </button>
              </li>
            </ul>
          </div>
        </section>
        <footer class="modal-card-foot">
          <button class="button" @click="listModalActive = false">Close</button>
        </footer>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="deleteConfirmModalActive" class="modal is-active">
      <div class="modal-background" @click="deleteConfirmModalActive = false"></div>
      <div class="modal-card">
        <header class="modal-card-head has-background-danger">
          <p class="modal-card-title has-text-white">Confirm Delete</p>
          <button class="delete" aria-label="close" @click="deleteConfirmModalActive = false"></button>
        </header>
        <section class="modal-card-body">
          <div class="content">
            <p class="has-text-weight-semibold">Are you sure you want to delete this model?</p>
            <div class="notification is-warning is-light">
              <p class="mb-2"><strong>Model:</strong> <code>{{ modelToDelete }}</code></p>
              <p class="mb-0"><strong>Host:</strong> {{ selectedHost }}</p>
            </div>
            <p class="has-text-danger">
              <v-icon name="fa-exclamation-triangle" />
              This action cannot be undone. The model will be permanently removed from the host.
            </p>
          </div>
        </section>
        <footer class="modal-card-foot">
          <button
            class="button is-danger"
            @click="deleteModel"
            :class="{ 'is-loading': deleteInProgress }"
            :disabled="deleteInProgress"
          >
            Delete Model
          </button>
          <button class="button" @click="deleteConfirmModalActive = false" :disabled="deleteInProgress">
            Cancel
          </button>
        </footer>
      </div>
    </div>
  </div>
</template>

<script>
import { inject, watch } from 'vue';
import { formatDistanceToNow } from 'date-fns';

export default {
  data() {
    return {
      llmmonitor: inject('llmmonitor'),
      refreshState: inject('refreshState'),
      endpoints: null,
      intervalId: null,
      refreshInterval: 5000, // Default 5 seconds
      searchQuery: '',
      pullModalActive: false,
      chatModalActive: false,
      selectedHost: null,
      pullModelName: '',
      pullInProgress: false,
      pullProgress: 0,
      pullStatus: '',
      pullError: null,
      pullComplete: false,
      chatHistory: [],
      chatInput: '',
      chatLoading: false,
      availableModels: [],
      selectedModel: '',
      modelsLoading: false,
      listModalActive: false,
      listModels: [],
      listModelsLoading: false,
      deleteConfirmModalActive: false,
      modelToDelete: null,
      deleteInProgress: false,
    };
  },
  mounted() {
    this.fetchEndpoints();
    this.startRefresh();

    // Add keyboard shortcut listener
    window.addEventListener('keydown', this.handleKeyboardShortcut);
  },
  beforeUnmount() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
    }
    window.removeEventListener('keydown', this.handleKeyboardShortcut);
  },
  computed: {
    filteredEndpoints() {
      if (!this.endpoints || !this.searchQuery) return this.endpoints;

      const query = this.searchQuery.toLowerCase();
      return Object.fromEntries(
        Object.entries(this.endpoints).filter(([label, plugin]) => {
          const labelMatch = label.toLowerCase().includes(query);
          const modelsMatch = plugin.models?.some(model =>
            model.name.toLowerCase().includes(query)
          );
          return labelMatch || modelsMatch;
        })
      );
    }
  },
  methods: {
    handleKeyboardShortcut(event) {
      // Check for Cmd+K (Mac) or Ctrl+K (Windows/Linux)
      if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
        event.preventDefault();
        this.$refs.searchInput.focus();
      }
    },

    clearSearch() {
      this.searchQuery = '';
      this.$refs.searchInput.blur();
    },

    async fetchEndpoints() {
      this.refreshState.loading = true;
      const startTime = Date.now();

      try {
        const response = await this.llmmonitor.axios.get('/llmm');
        const endTime = Date.now();
        const elapsed = endTime - startTime;

        // Ensure loading shows for at least 200ms
        if (elapsed < 200) {
          await new Promise(resolve => setTimeout(resolve, 200 - elapsed));
        }

        this.endpoints = response.data.endpoints;
      } catch (error) {
        console.error('Error fetching endpoints:', error);
      } finally {
        this.refreshState.loading = false;
      }
    },
    startRefresh() {
      if (this.intervalId) {
        clearInterval(this.intervalId);
      }
      this.fetchEndpoints();
      this.intervalId = setInterval(this.fetchEndpoints, this.refreshInterval);
    },
    updateRefreshInterval() {
      this.startRefresh(); // Restart with new interval
    },
    calculateVramUsage(models) {
      if (!models || models.length === 0) return 0;
      const totalVram = models.reduce((acc, model) => acc + (model.size_vram || 0), 0);
      return (totalVram / (16 * 1024 ** 3)) * 100; // Convert to percentage of 16GB
    },
    formatVramUsage(models) {
      if (!models || models.length === 0) return '0%';
      const totalVram = models.reduce((acc, model) => acc + (model.size_vram || 0), 0);
      const percentage = (totalVram / (16 * 1024 ** 3)) * 100;
      return `${percentage.toFixed(1)}%`;
    },
    getVramClass(models) {
      const usage = this.calculateVramUsage(models);
      if (usage > 80) return 'is-danger';
      if (usage > 60) return 'is-warning';
      return 'is-success';
    },
    formatRam(totalRamGb) {
      if (!totalRamGb) return 'N/A';
      return `${totalRamGb} GB`;
    },
    formatTimeRemaining(models) {
      if (!models || models.length === 0) return 'N/A';
      const latestExpiry = models.reduce((latest, model) => {
        if (!model.expires_at) return latest;
        const expiryTime = new Date(model.expires_at);
        return latest ? (expiryTime > latest ? expiryTime : latest) : expiryTime;
      }, null);
      if (!latestExpiry) return 'N/A';
      return formatDistanceToNow(latestExpiry, { addSuffix: true });
    },
    openPullModal(label) {
      this.selectedHost = label;
      this.pullModalActive = true;
      this.pullModelName = '';
      this.pullProgress = 0;
      this.pullStatus = '';
      this.pullError = null;
      this.pullComplete = false;
      this.pullInProgress = false;
    },
    async openListModal(label) {
      this.selectedHost = label;
      this.listModalActive = true;
      this.listModels = [];
      this.listModelsLoading = true;

      // Fetch available models for this host
      try {
        const response = await this.llmmonitor.axios.get(`/llmm/${label}/models`);
        this.listModels = response.data.models || [];
      } catch (error) {
        console.error('Error fetching models:', error);
        this.listModels = [];
      } finally {
        this.listModelsLoading = false;
      }
    },
    async openChatModal(label) {
      this.selectedHost = label;
      this.chatModalActive = true;
      this.chatHistory = [];
      this.chatInput = '';
      this.chatLoading = false;
      this.availableModels = [];
      this.selectedModel = '';
      this.modelsLoading = true;

      // Fetch available models for this host
      try {
        const response = await this.llmmonitor.axios.get(`/llmm/${label}/models`);
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
    closePullModal() {
      this.pullModalActive = false;
      this.pullModelName = '';
      this.pullProgress = 0;
      this.pullStatus = '';
      this.pullError = null;
      this.pullComplete = false;
      this.pullInProgress = false;
    },
    async startPull() {
      if (!this.pullModelName) return;

      this.pullInProgress = true;
      this.pullProgress = 0;
      this.pullStatus = 'Starting pull...';
      this.pullError = null;
      this.pullComplete = false;

      try {
        const response = await fetch(
          `${this.llmmonitor.axios.defaults.baseURL}/llmm/${this.selectedHost}/pull`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model_name: this.pullModelName }),
          }
        );

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n').filter(line => line.trim());

          for (const line of lines) {
            try {
              const data = JSON.parse(line);

              if (data.error) {
                this.pullError = data.error;
                this.pullInProgress = false;
                return;
              }

              if (data.status) {
                this.pullStatus = data.status;
              }

              if (data.completed && data.total) {
                this.pullProgress = Math.round((data.completed / data.total) * 100);
              }

              if (data.status === 'success') {
                this.pullComplete = true;
                this.pullInProgress = false;
              }
            } catch (e) {
              console.error('Error parsing pull progress:', e);
            }
          }
        }

        if (!this.pullComplete) {
          this.pullComplete = true;
          this.pullStatus = 'Pull completed';
        }
      } catch (error) {
        console.error('Error pulling model:', error);
        this.pullError = error.message || 'Failed to pull model';
      } finally {
        this.pullInProgress = false;
      }
    },
    async sendMessage() {
      if (!this.chatInput.trim()) return;

      const userMessage = { role: 'user', content: this.chatInput };
      this.chatHistory.push(userMessage);

      const messageToSend = this.chatInput;
      this.chatInput = '';
      this.chatLoading = true;

      try {
        const response = await fetch(
          `${this.llmmonitor.axios.defaults.baseURL}/llmm/${this.selectedHost}/chat`,
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
    confirmDeleteModel(modelName) {
      this.modelToDelete = modelName;
      this.deleteConfirmModalActive = true;
    },
    async deleteModel() {
      if (!this.modelToDelete) return;

      this.deleteInProgress = true;

      try {
        const response = await this.llmmonitor.axios.delete(
          `/llmm/${this.selectedHost}/delete`,
          {
            data: { model_name: this.modelToDelete }
          }
        );

        if (response.data.status === 'success') {
          // Close confirmation modal
          this.deleteConfirmModalActive = false;
          this.modelToDelete = null;

          // Refresh the model list
          this.listModelsLoading = true;
          try {
            const refreshResponse = await this.llmmonitor.axios.get(`/llmm/${this.selectedHost}/models`);
            this.listModels = refreshResponse.data.models || [];
          } catch (error) {
            console.error('Error refreshing models:', error);
          } finally {
            this.listModelsLoading = false;
          }
        }
      } catch (error) {
        console.error('Error deleting model:', error);
        alert(`Failed to delete model: ${error.response?.data?.detail || error.message}`);
      } finally {
        this.deleteInProgress = false;
      }
    },
    openFullscreenChat() {
      // Navigate to the fullscreen chat route
      this.$router.push(`/chat/${this.selectedHost}`);
    },
  },
};
</script>

<style scoped>
.llm-monitor {
  padding: 1.5rem;
}

.header-section {
  margin-bottom: 2rem;
}

.title {
  font-size: 1.75rem;
  margin-bottom: 0.5rem;
  color: #363636;
}

.subtitle {
  color: #666;
  font-size: 1rem;
}

.level {
  margin-bottom: 0.5rem;
}

.search-container {
  margin-bottom: 1rem;
  padding: 1rem;
  border-bottom: 1px solid #eee;
}

.search-field {
  width: 100%;
  position: relative;
  display: flex;
  align-items: center;
  background: #f5f5f5;
  border-radius: 6px;
  padding: 0.5rem 1rem;
}

.search-icon {
  color: #666;
  margin-right: 0.5rem;
  font-size: 0.875rem;
}

.search-field input {
  background: transparent;
  border: none;
  color: #333;
  font-size: 0.875rem;
  width: 100%;
  padding-right: 3rem;
}

.search-field input::placeholder {
  color: #666;
}

.search-field input:focus {
  outline: none;
}

.shortcut-hint {
  position: absolute;
  right: 0.75rem;
  color: #666;
  font-size: 0.75rem;
  background: #e0e0e0;
  padding: 0.125rem 0.375rem;
  border-radius: 4px;
}

.refresh-controls {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.loading-spinner {
  color: #7957d5;
  font-size: 0.875rem;
}

.table-container {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 3px rgba(0,0,0,0.1);
}

.table {
  width: 100%;
}

.table th {
  font-weight: 600;
  color: #363636;
}

.system-name {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #ff3860;
}

.status-dot.is-online {
  background-color: #23d160;
}

.ram-info {
  font-size: 0.9rem;
  color: #363636;
  font-weight: 500;
}

.vram-usage {
  width: 100%;
  max-width: 200px;
}

.progress {
  height: 0.5rem;
  margin-bottom: 0.25rem;
}

.vram-text {
  font-size: 0.8rem;
  color: #666;
}

.models-list {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.25em 0.75em;
  border-radius: 1rem;
  font-size: 0.8rem;
  font-weight: 500;
}

.status-badge.is-success {
  background-color: #ebfbee;
  color: #257942;
}

.status-badge.is-danger {
  background-color: #feecf0;
  color: #cc0f35;
}

.buttons.are-small .button {
  height: 2rem;
  padding: 0 0.75rem;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
}

.loading-content {
  text-align: center;
}

.loading-icon {
  font-size: 3rem;
  color: #7957d5;
  margin-bottom: 1rem;
  animation: fa-spin 1.2s infinite linear;
}

.loading-title {
  font-size: 1.5rem;
  color: #363636;
  margin-bottom: 0.5rem;
}

.loading-text {
  color: #666;
  font-size: 1rem;
}

@keyframes fa-spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Modal Styles */
.modal-card {
  max-width: 600px;
  margin: 0 auto;
}

.chat-modal {
  max-width: 800px;
  max-height: 80vh;
}

.modal-header-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.chat-body {
  height: 500px;
  padding: 0;
  display: flex;
  flex-direction: column;
}

.model-selector-container {
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #dbdbdb;
  background-color: #fafafa;
}

.model-selector-container .field {
  margin-bottom: 0;
}

.model-selector-container .label {
  font-size: 0.875rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.model-selector-container .select {
  width: 100%;
}

.model-selector-container .select select {
  width: 100%;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
}

.message-item {
  margin-bottom: 1rem;
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
  padding: 0.75rem 1rem;
  border-radius: 1rem;
  background-color: #f5f5f5;
}

.user-message .message-bubble {
  background-color: #3273dc;
  color: white;
}

.assistant-message .message-bubble {
  background-color: #f5f5f5;
  color: #363636;
}

.message-bubble strong {
  display: block;
  margin-bottom: 0.25rem;
  font-size: 0.875rem;
}

.message-bubble p {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.chat-footer {
  padding: 1rem;
  display: flex;
  gap: 0.5rem;
}

.progress-section {
  margin-top: 1rem;
}

.pull-status {
  margin-top: 0.5rem;
  font-size: 0.875rem;
  color: #666;
}

.ip-address {
  font-size: 0.9rem;
  color: #363636;
  font-weight: 500;
  font-family: monospace;
}

/* List Modal Styles */
.models-list-container {
  padding: 0.5rem 0;
}

.model-items {
  list-style: none;
  padding: 0;
  margin: 0;
}

.model-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-radius: 6px;
  margin-bottom: 0.5rem;
  background-color: #f9f9f9;
  border: 1px solid #e8e8e8;
  transition: background-color 0.2s ease;
}

.model-item:hover {
  background-color: #f0f0f0;
}

.model-item:last-child {
  margin-bottom: 0;
}

.model-item-content {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
}

.model-name {
  font-family: monospace;
  font-size: 0.95rem;
  color: #363636;
}
</style>
