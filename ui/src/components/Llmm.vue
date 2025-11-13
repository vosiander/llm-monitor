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
                  <option :value="1000">1s (adaptive)</option>
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
      <div v-if="selectedHosts.length > 0 && litellmStatus.available" class="bulk-actions-bar">
        <div class="level">
          <div class="level-left">
            <div class="level-item">
              <span class="has-text-weight-semibold">{{ selectedHosts.length }} host(s) selected</span>
            </div>
          </div>
          <div class="level-right">
            <div class="level-item">
              <button class="button is-success" @click="openLitellmModal">
                <span class="icon">
                  <v-icon name="fa-plus-circle" />
                </span>
                <span>Create in LiteLLM</span>
              </button>
              <button class="button is-danger ml-2" @click="openLitellmPurgeModal">
                <span class="icon">
                  <v-icon name="fa-fire" />
                </span>
                <span>Purge from LiteLLM</span>
              </button>
              <button class="button is-light ml-2" @click="selectedHosts = []">
                <span class="icon">
                  <v-icon name="fa-times" />
                </span>
                <span>Clear Selection</span>
              </button>
            </div>
          </div>
        </div>
      </div>
      <table class="table is-fullwidth">
        <thead>
          <tr>
            <th v-if="litellmStatus.available" style="width: 40px;">
              <input
                type="checkbox"
                @change="toggleSelectAll"
                :checked="allSelected"
                :indeterminate.prop="someSelected"
              >
            </th>
            <th>
              <span class="icon-text">
                <span class="icon"><v-icon name="fa-server" /></span>
                <span>System</span>
              </span>
            </th>
            <th>
              <span class="icon-text">
                <span class="icon"><v-icon name="fa-tag" /></span>
                <span>Version</span>
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
            <td v-if="litellmStatus.available">
              <input
                type="checkbox"
                :checked="selectedHosts.includes(label)"
                @change="toggleHostSelection(label)"
              >
            </td>
            <td>
              <div class="system-name">
                <span class="status-dot" :class="{ 'is-online': plugin.is_online }"></span>
                {{ label }}
              </div>
            </td>
            <td>
              <span class="version-text">{{ plugin.version || '-' }}</span>
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
              <div class="dropdown is-right" :class="{ 'is-active': activeDropdown === label }">
                <div class="dropdown-trigger">
                  <button
                    class="button is-small"
                    @click="toggleDropdown(label)"
                    aria-haspopup="true"
                    :aria-controls="`dropdown-menu-${label}`"
                  >
                    <span class="icon">
                      <v-icon name="fa-ellipsis-v" />
                    </span>
                  </button>
                </div>
                <div class="dropdown-menu" :id="`dropdown-menu-${label}`" role="menu" @click="closeDropdown">
                  <div class="dropdown-content">
                    <a href="#" class="dropdown-item" @click.prevent="openListModal(label)">
                      <span class="icon">
                        <v-icon name="fa-list" />
                      </span>
                      <span>List Models</span>
                    </a>
                    <a v-if="litellmStatus.available" href="#" class="dropdown-item" @click.prevent="openLitellmListModal(label)">
                      <span class="icon">
                        <v-icon name="fa-server" />
                      </span>
                      <span>LiteLLM Models</span>
                    </a>
                    <a href="#" class="dropdown-item" @click.prevent="openPullModal(label)">
                      <span class="icon">
                        <v-icon name="fa-download" />
                      </span>
                      <span>Pull Model</span>
                    </a>
                    <a href="#" class="dropdown-item" @click.prevent="openChatModal(label)">
                      <span class="icon">
                        <v-icon name="fa-comments" />
                      </span>
                      <span>Run Chat</span>
                    </a>
                  </div>
                </div>
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

    <!-- LiteLLM Bulk Create Modal -->
    <div v-if="litellmModalActive" class="modal is-active">
      <div class="modal-background" @click="litellmModalActive = false"></div>
      <div class="modal-card">
        <header class="modal-card-head has-background-success">
          <p class="modal-card-title has-text-white">Create Models in LiteLLM</p>
          <button class="delete" aria-label="close" @click="litellmModalActive = false"></button>
        </header>
        <section class="modal-card-body">
          <div class="field">
            <label class="label">Model Name</label>
            <div class="control">
              <input
                class="input"
                type="text"
                v-model="litellmModelName"
                placeholder="e.g., blablub-gemma3, my-llama3"
                :disabled="litellmCreating"
              >
            </div>
            <p class="help">The name for the LiteLLM model (e.g., "blablub-gemma3")</p>
          </div>

          <div class="field">
            <label class="label">Ollama Model</label>
            <div class="control">
              <input
                class="input"
                type="text"
                v-model="litellmOllamaModel"
                placeholder="ollama_chat/gemma3"
                :disabled="litellmCreating"
              >
            </div>
            <p class="help">The full Ollama model path (e.g., "ollama_chat/gemma3", "ollama_chat/llama3:8b")</p>
          </div>

          <div class="notification is-info is-light">
            <p class="mb-2"><strong>Selected Hosts ({{ selectedHosts.length }}):</strong></p>
            <ul class="ml-4">
              <li v-for="host in selectedHosts" :key="host">{{ host }}</li>
            </ul>
          </div>

          <div v-if="litellmModelName && litellmOllamaModel" class="notification is-light">
            <p class="has-text-weight-semibold mb-2">Configuration:</p>
            <div class="mt-3 mb-3">
              <p><strong>Model Name:</strong> <code>{{ litellmModelName }}</code></p>
              <p><strong>Ollama Model:</strong> <code>{{ litellmOllamaModel }}</code></p>
              <p class="mt-2"><strong>Will create:</strong> {{ selectedHosts.length }} model(s)</p>
            </div>
            <p class="help has-text-centered">Each host will have a model with ID "{host}-{{ litellmModelName }}"</p>
          </div>

          <div v-if="litellmCreating" class="notification is-info">
            <p><v-icon name="fa-circle-notch" class="fa-spin" /> Creating models in LiteLLM...</p>
          </div>

          <div v-if="litellmResults" class="results-section">
            <div class="notification" :class="litellmResults.failures === 0 ? 'is-success' : 'is-warning'">
              <p class="has-text-weight-semibold mb-2">
                Creation completed: {{ litellmResults.successes }} succeeded, {{ litellmResults.failures }} failed
              </p>
            </div>
            <div class="results-list">
              <div
                v-for="result in litellmResults.results"
                :key="result.host"
                class="result-item"
                :class="result.success ? 'is-success' : 'is-danger'"
              >
                <span class="icon">
                  <v-icon :name="result.success ? 'fa-check-circle' : 'fa-times-circle'" />
                </span>
                <span class="host-label">{{ result.host }}</span>
                <span v-if="result.success" class="model-name">→ {{ result.litellm_model_name }}</span>
                <span v-else class="error-text">{{ result.error }}</span>
              </div>
            </div>
          </div>
        </section>
        <footer class="modal-card-foot">
          <button
            v-if="!litellmResults"
            class="button is-success"
            @click="createLitellmModels"
            :disabled="!litellmModelName || !litellmOllamaModel || litellmCreating || selectedHosts.length === 0"
            :class="{ 'is-loading': litellmCreating }"
          >
            Create Models
          </button>
          <button class="button" @click="closeLitellmModal">
            {{ litellmResults ? 'Close' : 'Cancel' }}
          </button>
        </footer>
      </div>
    </div>

    <!-- LiteLLM List Models Modal -->
    <div v-if="litellmListModalActive" class="modal is-active">
      <div class="modal-background" @click="closeLitellmListModal"></div>
      <div class="modal-card">
        <header class="modal-card-head has-background-success">
          <p class="modal-card-title has-text-white">LiteLLM Models for {{ selectedHost }}</p>
          <button class="delete" aria-label="close" @click="closeLitellmListModal"></button>
        </header>
        <section class="modal-card-body">
          <div v-if="litellmListLoading" class="has-text-centered">
            <v-icon name="fa-circle-notch" class="fa-spin" style="font-size: 2rem; color: #48c774;" />
            <p class="mt-3">Loading LiteLLM models...</p>
          </div>
          <div v-else-if="litellmListModels.length === 0" class="has-text-centered">
            <p class="has-text-grey">No LiteLLM models found for this host</p>
            <p class="help mt-2">Models created for this host will appear here</p>
          </div>
          <div v-else class="models-list-container">
            <p class="has-text-weight-semibold mb-3">LiteLLM Models ({{ litellmListModels.length }}):</p>
            <ul class="model-items">
              <li v-for="model in litellmListModels" :key="model.model_info.id" class="model-item">
                <div class="model-item-content">
                  <span class="icon has-text-success">
                    <v-icon name="fa-server" />
                  </span>
                  <div class="model-info">
                    <div class="model-name">{{ model.model_name }}</div>
                    <div class="model-id">ID: {{ model.model_info.id }}</div>
                  </div>
                </div>
                <button
                  class="button is-danger is-small is-light"
                  @click="confirmDeleteLitellmModel(model.model_info.id)"
                  :disabled="litellmDeleteInProgress"
                  title="Delete model from LiteLLM"
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
          <button class="button" @click="closeLitellmListModal">Close</button>
        </footer>
      </div>
    </div>

    <!-- LiteLLM Delete Confirmation Modal -->
    <div v-if="litellmDeleteConfirmModal" class="modal is-active">
      <div class="modal-background" @click="litellmDeleteConfirmModal = false"></div>
      <div class="modal-card">
        <header class="modal-card-head has-background-danger">
          <p class="modal-card-title has-text-white">Confirm Delete from LiteLLM</p>
          <button class="delete" aria-label="close" @click="litellmDeleteConfirmModal = false"></button>
        </header>
        <section class="modal-card-body">
          <div class="content">
            <p class="has-text-weight-semibold">Are you sure you want to delete this model from LiteLLM?</p>
            <div class="notification is-warning is-light">
              <p class="mb-2"><strong>Model ID:</strong> <code>{{ litellmModelToDelete }}</code></p>
              <p class="mb-0"><strong>Host:</strong> {{ selectedHost }}</p>
            </div>
            <p class="has-text-danger">
              <v-icon name="fa-exclamation-triangle" />
              This will remove the model from LiteLLM but not from the Ollama host.
            </p>
          </div>
        </section>
        <footer class="modal-card-foot">
          <button
            class="button is-danger"
            @click="deleteLitellmModel"
            :class="{ 'is-loading': litellmDeleteInProgress }"
            :disabled="litellmDeleteInProgress"
          >
            Delete from LiteLLM
          </button>
          <button class="button" @click="litellmDeleteConfirmModal = false" :disabled="litellmDeleteInProgress">
            Cancel
          </button>
        </footer>
      </div>
    </div>

    <!-- LiteLLM Bulk Purge Modal -->
    <div v-if="litellmPurgeModalActive" class="modal is-active">
      <div class="modal-background" @click="litellmPurgeModalActive = false"></div>
      <div class="modal-card">
        <header class="modal-card-head has-background-danger">
          <p class="modal-card-title has-text-white">Purge Models from LiteLLM</p>
          <button class="delete" aria-label="close" @click="litellmPurgeModalActive = false"></button>
        </header>
        <section class="modal-card-body">
          <div v-if="!litellmPurgeResults">
            <div class="content">
              <p class="has-text-weight-semibold mb-3">
                <v-icon name="fa-exclamation-triangle" class="has-text-danger" />
                Warning: This will delete ALL LiteLLM models for the selected hosts!
              </p>
              <div class="notification is-danger is-light">
                <p class="mb-2"><strong>Selected Hosts ({{ selectedHosts.length }}):</strong></p>
                <ul class="ml-4">
                  <li v-for="host in selectedHosts" :key="host">{{ host }}</li>
                </ul>
              </div>
              <p class="has-text-danger">
                <v-icon name="fa-fire" />
                This action cannot be undone. All LiteLLM models for these hosts will be permanently removed.
              </p>
              <p class="help mt-3">
                Note: This only removes models from LiteLLM. Models will remain on the Ollama hosts.
              </p>
            </div>

            <div v-if="litellmPurging" class="notification is-danger">
              <p><v-icon name="fa-circle-notch" class="fa-spin" /> Purging models from LiteLLM...</p>
            </div>
          </div>

          <div v-if="litellmPurgeResults" class="results-section">
            <div class="notification" :class="litellmPurgeResults.failures === 0 ? 'is-success' : 'is-warning'">
              <p class="has-text-weight-semibold mb-2">
                Purge completed: {{ litellmPurgeResults.successes }} host(s) succeeded, {{ litellmPurgeResults.failures }} failed
              </p>
              <p class="mb-0">Total models deleted: {{ litellmPurgeResults.total_models_deleted }}</p>
            </div>
            <div class="results-list">
              <div
                v-for="result in litellmPurgeResults.results"
                :key="result.host"
                class="result-item"
                :class="result.success ? 'is-success' : 'is-danger'"
              >
                <span class="icon">
                  <v-icon :name="result.success ? 'fa-check-circle' : 'fa-times-circle'" />
                </span>
                <span class="host-label">{{ result.host }}</span>
                <span v-if="result.success" class="model-count">{{ result.models_deleted }} model(s) deleted</span>
                <span v-else class="error-text">{{ result.error }}</span>
              </div>
            </div>
          </div>
        </section>
        <footer class="modal-card-foot">
          <button
            v-if="!litellmPurgeResults"
            class="button is-danger"
            @click="purgeLitellmModels"
            :disabled="litellmPurging || selectedHosts.length === 0"
            :class="{ 'is-loading': litellmPurging }"
          >
            Purge All Models
          </button>
          <button class="button" @click="closeLitellmPurgeModal">
            {{ litellmPurgeResults ? 'Close' : 'Cancel' }}
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
      litellmStatus: inject('litellmStatus'),
      endpoints: null,
      intervalId: null,
      tickIntervalId: null,
      refreshInterval: 1000, // Default 1 second (adaptive mode)
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
      selectedHosts: [],
      litellmModalActive: false,
      litellmModelName: '',
      litellmOllamaModel: '',
      litellmCreating: false,
      litellmResults: null,
      litellmListModalActive: false,
      litellmListModels: [],
      litellmListLoading: false,
      litellmDeleteInProgress: false,
      litellmDeleteConfirmModal: false,
      litellmModelToDelete: null,
      litellmPurgeModalActive: false,
      litellmPurging: false,
      litellmPurgeResults: null,
      activeDropdown: null,
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
    if (this.tickIntervalId) {
      clearInterval(this.tickIntervalId);
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
    },
    allSelected() {
      if (!this.endpoints) return false;
      const allHosts = Object.keys(this.endpoints);
      return allHosts.length > 0 && this.selectedHosts.length === allHosts.length;
    },
    someSelected() {
      return this.selectedHosts.length > 0 && !this.allSelected;
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
    async sendTick() {
      try {
        await this.llmmonitor.axios.post('/llmm/tick');
      } catch (error) {
        console.error('Error sending tick:', error);
      }
    },
    startRefresh() {
      // Clear any existing intervals
      if (this.intervalId) {
        clearInterval(this.intervalId);
      }
      if (this.tickIntervalId) {
        clearInterval(this.tickIntervalId);
      }

      // Initial fetch
      this.fetchEndpoints();

      if (this.refreshInterval === 1000) {
        // Adaptive mode: send tick every second, poll cache every 2 seconds
        this.tickIntervalId = setInterval(this.sendTick, 1000);
        this.intervalId = setInterval(this.fetchEndpoints, 2000);
      } else {
        // Fixed interval mode: just poll cache at selected interval
        this.intervalId = setInterval(this.fetchEndpoints, this.refreshInterval);
      }
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
    toggleSelectAll() {
      if (this.allSelected) {
        this.selectedHosts = [];
      } else {
        this.selectedHosts = Object.keys(this.endpoints || {});
      }
    },
    toggleHostSelection(label) {
      const index = this.selectedHosts.indexOf(label);
      if (index > -1) {
        this.selectedHosts.splice(index, 1);
      } else {
        this.selectedHosts.push(label);
      }
    },
    openLitellmModal() {
      this.litellmModalActive = true;
      this.litellmModelName = '';
      this.litellmOllamaModel = '';
      this.litellmCreating = false;
      this.litellmResults = null;
    },
    async createLitellmModels() {
      if (!this.litellmModelName || !this.litellmOllamaModel || this.selectedHosts.length === 0) return;

      this.litellmCreating = true;
      this.litellmResults = null;

      try {
        const response = await this.llmmonitor.axios.post('/llmm/litellm/models/bulk-create', {
          model_name: this.litellmModelName,
          ollama_model: this.litellmOllamaModel,
          host_labels: this.selectedHosts
        });

        this.litellmResults = response.data;
      } catch (error) {
        console.error('Error creating LiteLLM models:', error);
        alert(`Failed to create models: ${error.response?.data?.detail || error.message}`);
      } finally {
        this.litellmCreating = false;
      }
    },
    closeLitellmModal() {
      this.litellmModalActive = false;
      this.litellmModelName = '';
      this.litellmOllamaModel = '';
      this.litellmCreating = false;
      this.litellmResults = null;
      // Clear selection after closing
      this.selectedHosts = [];
    },
    async openLitellmListModal(label) {
      this.selectedHost = label;
      this.litellmListModalActive = true;
      this.litellmListModels = [];
      this.litellmListLoading = true;

      // Fetch LiteLLM models for this host
      try {
        const response = await this.llmmonitor.axios.get(`/llmm/litellm/models/${label}`);
        this.litellmListModels = response.data.models || [];
      } catch (error) {
        console.error('Error fetching LiteLLM models:', error);
        this.litellmListModels = [];
      } finally {
        this.litellmListLoading = false;
      }
    },
    closeLitellmListModal() {
      this.litellmListModalActive = false;
      this.litellmListModels = [];
      this.litellmListLoading = false;
    },
    confirmDeleteLitellmModel(modelId) {
      this.litellmModelToDelete = modelId;
      this.litellmDeleteConfirmModal = true;
    },
    async deleteLitellmModel() {
      if (!this.litellmModelToDelete) return;

      this.litellmDeleteInProgress = true;

      try {
        const response = await this.llmmonitor.axios.delete(
          `/llmm/litellm/models/${this.litellmModelToDelete}`
        );

        if (response.data.status === 'success') {
          // Close confirmation modal
          this.litellmDeleteConfirmModal = false;
          this.litellmModelToDelete = null;

          // Refresh the LiteLLM model list
          this.litellmListLoading = true;
          try {
            const refreshResponse = await this.llmmonitor.axios.get(`/llmm/litellm/models/${this.selectedHost}`);
            this.litellmListModels = refreshResponse.data.models || [];
          } catch (error) {
            console.error('Error refreshing LiteLLM models:', error);
          } finally {
            this.litellmListLoading = false;
          }
        }
      } catch (error) {
        console.error('Error deleting LiteLLM model:', error);
        alert(`Failed to delete model from LiteLLM: ${error.response?.data?.detail || error.message}`);
      } finally {
        this.litellmDeleteInProgress = false;
      }
    },
    openLitellmPurgeModal() {
      this.litellmPurgeModalActive = true;
      this.litellmPurging = false;
      this.litellmPurgeResults = null;
    },
    async purgeLitellmModels() {
      if (this.selectedHosts.length === 0) return;

      this.litellmPurging = true;
      this.litellmPurgeResults = null;

      try {
        const response = await this.llmmonitor.axios.post('/llmm/litellm/models/bulk-purge', {
          host_labels: this.selectedHosts
        });

        this.litellmPurgeResults = response.data;
      } catch (error) {
        console.error('Error purging LiteLLM models:', error);
        alert(`Failed to purge models: ${error.response?.data?.detail || error.message}`);
      } finally {
        this.litellmPurging = false;
      }
    },
    closeLitellmPurgeModal() {
      this.litellmPurgeModalActive = false;
      this.litellmPurging = false;
      this.litellmPurgeResults = null;
      // Clear selection after closing
      this.selectedHosts = [];
    },
    toggleDropdown(label) {
      if (this.activeDropdown === label) {
        this.activeDropdown = null;
      } else {
        this.activeDropdown = label;
      }
    },
    closeDropdown() {
      this.activeDropdown = null;
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
  overflow: visible;
}

.table {
  width: 100%;
  overflow: visible;
}

.table tbody {
  overflow: visible;
}

.table tbody tr {
  overflow: visible;
}

.table tbody tr td {
  overflow: visible;
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

.version-text {
  font-size: 0.85rem;
  color: #7957d5;
  font-weight: 600;
  font-family: monospace;
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
  font-weight: 600;
}

.model-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.model-id {
  font-family: monospace;
  font-size: 0.75rem;
  color: #999;
}

/* Bulk Actions Bar */
.bulk-actions-bar {
  padding: 1rem 1.5rem;
  background-color: #f0f9ff;
  border-bottom: 2px solid #3298dc;
  margin-bottom: 0;
}

.bulk-actions-bar .level {
  margin-bottom: 0;
}

/* LiteLLM Results */
.results-section {
  margin-top: 1rem;
}

.results-list {
  margin-top: 0.75rem;
}

.result-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border-radius: 6px;
  margin-bottom: 0.5rem;
  background-color: #f9f9f9;
  border: 1px solid #e8e8e8;
}

.result-item.is-success {
  background-color: #ebfbee;
  border-color: #48c774;
}

.result-item.is-danger {
  background-color: #feecf0;
  border-color: #f14668;
}

.result-item .icon {
  font-size: 1.25rem;
}

.result-item.is-success .icon {
  color: #48c774;
}

.result-item.is-danger .icon {
  color: #f14668;
}

.result-item .host-label {
  font-weight: 600;
  min-width: 150px;
}

.result-item .model-name {
  font-family: monospace;
  color: #363636;
}

.result-item .error-text {
  color: #f14668;
  font-size: 0.875rem;
}

/* Dropdown z-index fix - ensure dropdown appears above table content */
.dropdown {
  position: relative;
}

.dropdown-menu {
  z-index: 100;
}

.dropdown.is-active .dropdown-menu {
  display: block;
}
</style>
