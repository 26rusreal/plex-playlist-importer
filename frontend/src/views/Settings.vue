<template>
  <div class="settings">
    <!-- Auth Card -->
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">Plex Account</h2>
        <div class="status-indicator">
          <span class="status-dot" :class="connected ? 'connected' : 'disconnected'"></span>
          <span>{{ connected ? 'Connected' : 'Not connected' }}</span>
        </div>
      </div>
      
      <!-- Logged in state -->
      <div v-if="user" class="user-info">
        <img v-if="user.thumb" :src="user.thumb" class="user-avatar" alt="avatar">
        <div class="user-details">
          <div class="user-name">{{ user.username }}</div>
          <div class="user-email">{{ user.email }}</div>
        </div>
        <button class="btn btn-secondary" @click="logout">
          Logout
        </button>
      </div>
      
      <!-- Login button -->
      <div v-else class="auth-section">
        <p class="auth-description">
          Sign in with your Plex account to automatically configure the connection.
        </p>
        <button class="btn btn-plex" @click="startAuth" :disabled="authInProgress">
          <svg class="plex-icon" viewBox="0 0 24 24" width="20" height="20">
            <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
          </svg>
          {{ authInProgress ? 'Waiting for authorization...' : 'Sign in with Plex' }}
        </button>
        
        <!-- Auth popup info -->
        <div v-if="authInProgress" class="auth-waiting">
          <div class="spinner"></div>
          <p>A new window should have opened. Please sign in to Plex.</p>
          <p class="auth-hint">If the window didn't open, <a :href="authUrl" target="_blank">click here</a></p>
          <button class="btn btn-sm btn-secondary" @click="cancelAuth">Cancel</button>
        </div>
      </div>
    </div>
    
    <!-- Server Selection -->
    <div class="card" v-if="servers.length > 0 || settings.plex_url">
      <div class="card-header">
        <h2 class="card-title">Plex Server</h2>
      </div>
      
      <div v-if="message" :class="['alert', messageType === 'success' ? 'alert-success' : 'alert-error']">
        {{ message }}
      </div>
      
      <!-- Server list from account -->
      <div v-if="servers.length > 0" class="server-list">
        <div 
          v-for="server in servers" 
          :key="server.clientIdentifier"
          class="server-item"
          :class="{ selected: settings.plex_url === server.url }"
          @click="selectServer(server)"
        >
          <div class="server-info">
            <div class="server-name">
              {{ server.name }}
              <span v-if="server.owned" class="badge badge-info">Owner</span>
              <span v-if="server.local" class="badge badge-success">Local</span>
            </div>
            <div class="server-url">{{ server.url }}</div>
          </div>
          <div v-if="settings.plex_url === server.url" class="server-check">✓</div>
        </div>
      </div>
      
      <!-- Manual URL input -->
      <div class="form-group" style="margin-top: 16px;">
        <label class="form-label">Server URL (or enter manually)</label>
        <input 
          v-model="settings.plex_url" 
          type="text" 
          class="form-input"
          placeholder="http://localhost:32400"
        >
      </div>
    </div>
    
    <!-- Library & Path Settings -->
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">Library Settings</h2>
      </div>
      
      <form @submit.prevent="saveSettings">
        <div class="form-group">
          <label class="form-label">Music Library</label>
          <select v-model="settings.music_library_name" class="form-input" v-if="libraries.length">
            <option v-for="lib in libraries" :key="lib.name" :value="lib.name">
              {{ lib.name }}
            </option>
          </select>
          <input 
            v-else
            v-model="settings.music_library_name" 
            type="text" 
            class="form-input"
            placeholder="Music"
          >
        </div>
        
        <div class="form-group">
          <label class="form-label">Playlists Folder (inside container)</label>
          <input 
            v-model="settings.playlists_path" 
            type="text" 
            class="form-input"
            placeholder="/playlists"
          >
        </div>
        
        <div style="display: flex; gap: 12px;">
          <button type="button" class="btn btn-secondary" @click="testConnection" :disabled="testing">
            <span v-if="testing" class="spinner"></span>
            Test Connection
          </button>
          <button type="submit" class="btn btn-primary" :disabled="saving">
            <span v-if="saving" class="spinner"></span>
            Save Settings
          </button>
        </div>
      </form>
    </div>
    
    <!-- Manual Token (collapsed) -->
    <details class="card">
      <summary class="card-header" style="cursor: pointer;">
        <h2 class="card-title">Manual Token Entry (Advanced)</h2>
      </summary>
      <div style="padding-top: 16px;">
        <div class="form-group">
          <label class="form-label">Plex Token</label>
          <input 
            v-model="manualToken" 
            type="password" 
            class="form-input"
            placeholder="Enter token manually"
          >
        </div>
        <button class="btn btn-secondary" @click="saveManualToken" :disabled="!manualToken">
          Save Token
        </button>
        
        <div style="margin-top: 16px; color: var(--text-secondary); font-size: 13px;">
          <p><strong>How to get token manually:</strong></p>
          <ol style="padding-left: 20px; line-height: 2;">
            <li>Open Plex Web App and sign in</li>
            <li>Browse to any media item</li>
            <li>Click (...) → Get Info → View XML</li>
            <li>Copy X-Plex-Token from URL</li>
          </ol>
        </div>
      </div>
    </details>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'Settings',
  data() {
    return {
      settings: {
        plex_url: '',
        plex_token: '',
        music_library_name: 'Music',
        playlists_path: '/playlists'
      },
      manualToken: '',
      libraries: [],
      servers: [],
      user: null,
      connected: false,
      testing: false,
      saving: false,
      message: '',
      messageType: '',
      // OAuth
      authInProgress: false,
      authUrl: '',
      authCode: '',
      authCheckInterval: null
    }
  },
  async mounted() {
    await this.loadSettings()
    await this.loadServers()
  },
  beforeUnmount() {
    this.cancelAuth()
  },
  methods: {
    async loadSettings() {
      try {
        const { data } = await axios.get('/api/settings')
        if (data.plex_url) this.settings.plex_url = data.plex_url
        if (data.music_library_name) this.settings.music_library_name = data.music_library_name
        if (data.playlists_path) this.settings.playlists_path = data.playlists_path
        
        // Check if we have a token
        if (data.plex_token_set) {
          await this.fetchLibraries()
        }
      } catch (error) {
        console.error('Failed to load settings:', error)
      }
    },
    
    async loadServers() {
      try {
        const { data } = await axios.get('/api/auth/servers')
        this.servers = data
        
        // If we have servers, we're logged in - try to get user info
        if (this.servers.length > 0) {
          this.connected = true
          // Mock user from first server
          this.user = {
            username: 'Plex User',
            email: '',
            thumb: ''
          }
        }
      } catch (error) {
        // Not logged in or error
        this.servers = []
      }
    },
    
    async fetchLibraries() {
      try {
        const { data } = await axios.get('/api/libraries')
        this.libraries = data
        this.connected = true
        
        // Auto-select library if current selection is invalid or empty
        if (this.libraries.length > 0) {
          const currentValid = this.libraries.some(l => l.name === this.settings.music_library_name)
          if (!currentValid) {
            this.settings.music_library_name = this.libraries[0].name
            // Auto-save the correct library
            await this.saveSettings()
          }
        }
      } catch (error) {
        this.connected = false
      }
    },
    
    // ===== OAuth Methods =====
    
    async startAuth() {
      this.authInProgress = true
      this.message = ''
      
      try {
        const { data } = await axios.post('/api/auth/start')
        this.authUrl = data.auth_url
        this.authCode = data.code
        
        // Open auth window
        const authWindow = window.open(
          data.auth_url,
          'PlexAuth',
          'width=600,height=700,menubar=no,toolbar=no'
        )
        
        // Start polling for auth completion
        this.authCheckInterval = setInterval(async () => {
          try {
            const { data: checkData } = await axios.get(`/api/auth/check/${this.authCode}`)
            
            if (checkData.authorized) {
              // Success!
              clearInterval(this.authCheckInterval)
              this.authCheckInterval = null
              this.authInProgress = false
              
              // Close popup if still open
              if (authWindow && !authWindow.closed) {
                authWindow.close()
              }
              
              // Update state
              this.user = checkData.user
              this.servers = checkData.servers || []
              
              // Auto-select first server if available
              if (this.servers.length > 0) {
                this.selectServer(this.servers[0])
              }
              
              // Save token
              await axios.post('/api/auth/save', {
                token: checkData.token,
                client_id: checkData.client_id,
                server_url: this.servers.length > 0 ? this.servers[0].url : null
              })
              
              this.connected = true
              this.message = 'Successfully signed in!'
              this.messageType = 'success'
              
              await this.fetchLibraries()
            }
          } catch (error) {
            console.error('Auth check error:', error)
          }
        }, 2000)
        
        // Timeout after 2 minutes
        setTimeout(() => {
          if (this.authInProgress) {
            this.cancelAuth()
            this.message = 'Authorization timed out. Please try again.'
            this.messageType = 'error'
          }
        }, 120000)
        
      } catch (error) {
        this.authInProgress = false
        this.message = error.response?.data?.detail || 'Failed to start authentication'
        this.messageType = 'error'
      }
    },
    
    cancelAuth() {
      if (this.authCheckInterval) {
        clearInterval(this.authCheckInterval)
        this.authCheckInterval = null
      }
      this.authInProgress = false
      this.authUrl = ''
      this.authCode = ''
    },
    
    async logout() {
      try {
        await axios.post('/api/auth/logout')
        this.user = null
        this.servers = []
        this.connected = false
        this.libraries = []
        this.message = 'Logged out'
        this.messageType = 'success'
      } catch (error) {
        this.message = 'Failed to logout'
        this.messageType = 'error'
      }
    },
    
    // ===== Server & Settings Methods =====
    
    selectServer(server) {
      this.settings.plex_url = server.url
      // If server has its own access token, we might want to use it
      // but usually the main token works fine
    },
    
    async saveManualToken() {
      if (!this.manualToken) return
      
      try {
        await axios.post('/api/auth/save', {
          token: this.manualToken
        })
        this.manualToken = ''
        this.message = 'Token saved!'
        this.messageType = 'success'
        await this.loadSettings()
        await this.fetchLibraries()
      } catch (error) {
        this.message = error.response?.data?.detail || 'Failed to save token'
        this.messageType = 'error'
      }
    },
    
    async testConnection() {
      this.testing = true
      this.message = ''
      
      try {
        const settings = await axios.get('/api/settings')
        const token = settings.data.plex_token_set ? '***existing***' : ''
        
        const { data } = await axios.post('/api/test-connection', {
          plex_url: this.settings.plex_url,
          plex_token: token
        })
        
        this.message = data.message
        this.messageType = 'success'
        this.libraries = data.libraries || []
        this.connected = true
        
        if (this.libraries.length && !this.settings.music_library_name) {
          this.settings.music_library_name = this.libraries[0].name
        }
      } catch (error) {
        this.message = error.response?.data?.detail || 'Connection failed'
        this.messageType = 'error'
        this.connected = false
      }
      
      this.testing = false
    },
    
    async saveSettings() {
      this.saving = true
      this.message = ''
      
      try {
        await axios.post('/api/settings', {
          ...this.settings,
          plex_token: '***keep***' // Signal to keep existing token
        })
        this.message = 'Settings saved!'
        this.messageType = 'success'
      } catch (error) {
        this.message = error.response?.data?.detail || 'Failed to save'
        this.messageType = 'error'
      }
      
      this.saving = false
    }
  }
}
</script>

<style scoped>
.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
}

/* User info */
.user-info {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: 8px;
}

.user-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
}

.user-details {
  flex: 1;
}

.user-name {
  font-weight: 600;
  font-size: 16px;
}

.user-email {
  color: var(--text-secondary);
  font-size: 13px;
}

/* Auth section */
.auth-section {
  text-align: center;
  padding: 20px;
}

.auth-description {
  color: var(--text-secondary);
  margin-bottom: 20px;
}

.btn-plex {
  background: #e5a00d;
  color: #000;
  font-weight: 600;
  padding: 12px 24px;
  font-size: 15px;
}

.btn-plex:hover:not(:disabled) {
  background: #f5b82e;
}

.plex-icon {
  margin-right: 8px;
}

.auth-waiting {
  margin-top: 24px;
  padding: 20px;
  background: var(--bg-secondary);
  border-radius: 8px;
}

.auth-waiting p {
  margin: 12px 0;
  color: var(--text-secondary);
}

.auth-waiting .spinner {
  margin: 0 auto 16px;
}

.auth-hint {
  font-size: 13px;
}

.auth-hint a {
  color: var(--accent);
}

/* Server list */
.server-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.server-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: 8px;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.2s;
}

.server-item:hover {
  background: var(--bg-hover);
}

.server-item.selected {
  border-color: var(--accent);
  background: var(--bg-hover);
}

.server-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.server-name {
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
}

.server-url {
  font-size: 13px;
  color: var(--text-secondary);
  font-family: monospace;
}

.server-check {
  color: var(--accent);
  font-size: 20px;
  font-weight: bold;
}

/* Details/summary for collapsible */
details.card > summary {
  list-style: none;
}

details.card > summary::-webkit-details-marker {
  display: none;
}

details.card > summary::after {
  content: '▶';
  float: right;
  transition: transform 0.2s;
}

details.card[open] > summary::after {
  transform: rotate(90deg);
}
</style>
