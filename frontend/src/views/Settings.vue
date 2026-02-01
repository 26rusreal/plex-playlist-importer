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
    
    <!-- Spotify Settings -->
    <div class="card spotify-settings">
      <div class="card-header">
        <h2 class="card-title">
          <svg viewBox="0 0 24 24" width="24" height="24" fill="#1DB954" style="vertical-align: middle; margin-right: 8px;">
            <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
          </svg>
          Spotify Integration
        </h2>
        <div class="status-indicator">
          <span class="status-dot" :class="spotifyConfigured ? 'connected' : 'disconnected'"></span>
          <span>{{ spotifyConfigured ? 'Configured' : 'Not configured' }}</span>
        </div>
      </div>
      
      <p class="spotify-description">
        Import playlists directly from Spotify. Requires free Spotify API credentials.
        <a href="https://developer.spotify.com/dashboard" target="_blank" rel="noopener">
          Create app on Spotify Developer Dashboard →
        </a>
      </p>
      
      <div v-if="spotifyMessage" :class="['alert', spotifyMessageType === 'success' ? 'alert-success' : 'alert-error']">
        {{ spotifyMessage }}
      </div>
      
      <div class="form-group">
        <label class="form-label">Client ID</label>
        <input 
          v-model="spotifyClientId" 
          type="text" 
          class="form-input"
          placeholder="Enter Spotify Client ID"
        >
      </div>
      
      <div class="form-group">
        <label class="form-label">Client Secret</label>
        <input 
          v-model="spotifyClientSecret" 
          type="password" 
          class="form-input"
          placeholder="Enter Spotify Client Secret"
        >
      </div>
      
      <button class="btn btn-spotify" @click="saveSpotifyCredentials" :disabled="savingSpotify || !spotifyClientId || !spotifyClientSecret">
        <span v-if="savingSpotify" class="spinner"></span>
        Save Spotify Credentials
      </button>
    </div>
    
    <!-- SLSKD Settings -->
    <div class="card slskd-settings">
      <div class="card-header">
        <h2 class="card-title">
          <span style="font-size: 20px; margin-right: 8px;">🎵</span>
          SLSKD Integration (Soulseek)
        </h2>
        <div class="status-indicator">
          <span class="status-dot" :class="slskdAvailable ? 'connected' : 'disconnected'"></span>
          <span>{{ slskdAvailable ? (slskdSettings.enabled ? 'Enabled' : 'Disabled') : 'Not configured' }}</span>
        </div>
      </div>
      
      <p class="slskd-description">
        Download missing tracks from Soulseek P2P network via SLSKD daemon.
        <a href="https://github.com/slskd/slskd" target="_blank" rel="noopener">
          Learn more about SLSKD →
        </a>
      </p>
      
      <div v-if="!slskdAvailable" class="alert alert-warning" style="margin-bottom: 16px;">
        SLSKD API key not configured. Set SLSKD_API_KEY environment variable.
      </div>
      
      <div v-if="slskdMessage" :class="['alert', slskdMessageType === 'success' ? 'alert-success' : 'alert-error']" style="margin-bottom: 16px;">
        {{ slskdMessage }}
      </div>
      
      <div class="form-group">
        <label class="checkbox">
          <input type="checkbox" v-model="slskdSettings.enabled" :disabled="!slskdAvailable">
          <span>Enable SLSKD Integration</span>
        </label>
      </div>
      
      <template v-if="slskdSettings.enabled && slskdAvailable">
        <div class="form-group">
          <label class="form-label">SLSKD URL</label>
          <div style="display: flex; gap: 12px;">
            <input 
              v-model="slskdSettings.url" 
              type="text" 
              class="form-input"
              placeholder="http://192.168.1.100:5030"
              style="flex: 1;"
            >
            <button class="btn btn-secondary" @click="testSlskdConnection" :disabled="slskdTesting || !slskdSettings.url">
              <span v-if="slskdTesting" class="spinner"></span>
              Test
            </button>
          </div>
        </div>
        
        <div class="form-group">
          <label class="form-label">Allowed File Extensions</label>
          <div class="extension-chips">
            <span 
              v-for="ext in slskdSettings.allowed_extensions" 
              :key="ext" 
              class="extension-chip"
            >
              {{ ext }}
              <button class="chip-remove" @click="removeExtension(ext)">&times;</button>
            </span>
          </div>
          <div style="display: flex; gap: 8px; margin-top: 8px;">
            <input 
              v-model="newExtension" 
              type="text" 
              class="form-input"
              placeholder="Add extension (e.g., flac)"
              style="flex: 1;"
              @keyup.enter="addExtension"
            >
            <button class="btn btn-secondary btn-sm" @click="addExtension" :disabled="!newExtension.trim()">
              Add
            </button>
          </div>
        </div>
        
        <div style="display: flex; gap: 16px; flex-wrap: wrap;">
          <div class="form-group" style="flex: 1; min-width: 150px;">
            <label class="form-label">Search Timeout (sec)</label>
            <input 
              v-model.number="slskdSettings.search_timeout" 
              type="number" 
              class="form-input"
              min="5"
              max="60"
            >
          </div>
          
          <div class="form-group" style="flex: 1; min-width: 150px;">
            <label class="form-label">Max Results</label>
            <input 
              v-model.number="slskdSettings.max_results" 
              type="number" 
              class="form-input"
              min="10"
              max="200"
            >
          </div>
          
          <div class="form-group" style="flex: 1; min-width: 150px;">
            <label class="form-label">Download Attempts</label>
            <input 
              v-model.number="slskdSettings.download_attempts" 
              type="number" 
              class="form-input"
              min="1"
              max="10"
            >
          </div>
        </div>
      </template>
      
      <button class="btn btn-slskd" @click="saveSlskdSettings" :disabled="savingSlskd">
        <span v-if="savingSlskd" class="spinner"></span>
        Save SLSKD Settings
      </button>
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
      authCheckInterval: null,
      // Spotify
      spotifyClientId: '',
      spotifyClientSecret: '',
      spotifyConfigured: false,
      savingSpotify: false,
      spotifyMessage: '',
      spotifyMessageType: '',
      // SLSKD
      slskdAvailable: false,
      slskdSettings: {
        enabled: false,
        url: 'http://localhost:5030',
        allowed_extensions: ['flac', 'mp3', 'wav', 'ogg', 'm4a'],
        search_timeout: 10,
        max_results: 50,
        download_attempts: 3
      },
      slskdTesting: false,
      savingSlskd: false,
      slskdMessage: '',
      slskdMessageType: '',
      newExtension: ''
    }
  },
  async mounted() {
    await this.loadSettings()
    await this.loadServers()
    await this.loadSpotifyStatus()
    await this.loadSlskdStatus()
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
    },
    
    // ===== Spotify Methods =====
    
    async loadSpotifyStatus() {
      try {
        const { data } = await axios.get('/api/spotify/credentials')
        this.spotifyConfigured = data.configured
        if (data.client_id) {
          this.spotifyClientId = data.client_id
        }
      } catch (error) {
        console.error('Failed to load Spotify status:', error)
      }
    },
    
    async saveSpotifyCredentials() {
      if (!this.spotifyClientId || !this.spotifyClientSecret) return
      
      this.savingSpotify = true
      this.spotifyMessage = ''
      
      try {
        await axios.post('/api/spotify/credentials', {
          client_id: this.spotifyClientId,
          client_secret: this.spotifyClientSecret
        })
        this.spotifyMessage = 'Spotify credentials saved!'
        this.spotifyMessageType = 'success'
        this.spotifyConfigured = true
        this.spotifyClientSecret = '' // Clear for security
      } catch (error) {
        this.spotifyMessage = error.response?.data?.detail || 'Failed to save'
        this.spotifyMessageType = 'error'
      }
      
      this.savingSpotify = false
    },
    
    // ===== SLSKD Methods =====
    
    async loadSlskdStatus() {
      try {
        const { data: status } = await axios.get('/api/slskd/status')
        this.slskdAvailable = status.available
        
        const { data: settings } = await axios.get('/api/slskd/settings')
        this.slskdSettings = settings
      } catch (error) {
        console.error('Failed to load SLSKD status:', error)
      }
    },
    
    async testSlskdConnection() {
      this.slskdTesting = true
      this.slskdMessage = ''
      
      try {
        const { data } = await axios.post('/api/slskd/test', {
          url: this.slskdSettings.url
        })
        this.slskdMessage = data.message || 'Connection successful!'
        this.slskdMessageType = 'success'
      } catch (error) {
        this.slskdMessage = error.response?.data?.detail || 'Connection failed'
        this.slskdMessageType = 'error'
      }
      
      this.slskdTesting = false
    },
    
    async saveSlskdSettings() {
      this.savingSlskd = true
      this.slskdMessage = ''
      
      try {
        await axios.post('/api/slskd/settings', this.slskdSettings)
        this.slskdMessage = 'SLSKD settings saved!'
        this.slskdMessageType = 'success'
      } catch (error) {
        this.slskdMessage = error.response?.data?.detail || 'Failed to save'
        this.slskdMessageType = 'error'
      }
      
      this.savingSlskd = false
    },
    
    addExtension() {
      const ext = this.newExtension.trim().toLowerCase().replace(/^\./, '')
      if (ext && !this.slskdSettings.allowed_extensions.includes(ext)) {
        this.slskdSettings.allowed_extensions.push(ext)
        this.newExtension = ''
      }
    },
    
    removeExtension(ext) {
      this.slskdSettings.allowed_extensions = this.slskdSettings.allowed_extensions.filter(e => e !== ext)
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

/* Spotify settings */
.spotify-settings {
  background: linear-gradient(135deg, rgba(29, 185, 84, 0.08) 0%, rgba(0, 0, 0, 0) 50%);
  border: 1px solid rgba(29, 185, 84, 0.2);
}

.spotify-description {
  color: var(--text-secondary);
  margin-bottom: 20px;
  font-size: 14px;
}

.spotify-description a {
  color: #1DB954;
  text-decoration: none;
}

.spotify-description a:hover {
  text-decoration: underline;
}

.btn-spotify {
  background: #1DB954;
  color: #fff;
  font-weight: 600;
}

.btn-spotify:hover:not(:disabled) {
  background: #1ed760;
}

/* SLSKD settings */
.slskd-settings {
  background: linear-gradient(135deg, rgba(100, 149, 237, 0.08) 0%, rgba(0, 0, 0, 0) 50%);
  border: 1px solid rgba(100, 149, 237, 0.2);
}

.slskd-description {
  color: var(--text-secondary);
  margin-bottom: 20px;
  font-size: 14px;
}

.slskd-description a {
  color: #6495ED;
  text-decoration: none;
}

.slskd-description a:hover {
  text-decoration: underline;
}

.btn-slskd {
  background: #6495ED;
  color: #fff;
  font-weight: 600;
}

.btn-slskd:hover:not(:disabled) {
  background: #7ba3f0;
}

.extension-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.extension-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 16px;
  font-size: 13px;
}

.chip-remove {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 16px;
  padding: 0;
  line-height: 1;
}

.chip-remove:hover {
  color: var(--error);
}

.alert-warning {
  background: rgba(229, 160, 13, 0.1);
  border: 1px solid rgba(229, 160, 13, 0.3);
  color: #e5a00d;
}
</style>
