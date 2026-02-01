<template>
  <div class="home">
    <!-- Hero Section with Icon -->
    <div class="hero-section">
      <img src="/playlist-icon.png" alt="Playlist Icon" class="hero-icon" />
      <div class="stats">
        <div class="stat-item">
          <div class="stat-value">{{ playlists.length }}</div>
          <div class="stat-label">Playlists Found</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">{{ totalTracks }}</div>
          <div class="stat-label">Total Tracks</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">{{ selectedPlaylists.length }}</div>
          <div class="stat-label">Selected</div>
        </div>
      </div>
    </div>
    
    <!-- Spotify Import Card -->
    <div class="card spotify-card">
      <div class="card-header">
        <h2 class="card-title">
          <svg viewBox="0 0 24 24" width="24" height="24" fill="#1DB954" style="vertical-align: middle; margin-right: 8px;">
            <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
          </svg>
          Import from Spotify
        </h2>
      </div>
      
      <div class="spotify-input-row">
        <input 
          v-model="spotifyUrl" 
          type="text" 
          class="form-input" 
          placeholder="Paste Spotify playlist URL (e.g. https://open.spotify.com/playlist/...)"
          @keyup.enter="previewSpotify"
        >
        <button 
          class="btn btn-primary" 
          @click="previewSpotify" 
          :disabled="!spotifyUrl || spotifyLoading"
        >
          <span v-if="spotifyLoading" class="spinner"></span>
          Preview
        </button>
      </div>
      
      <div v-if="spotifyError" class="alert alert-error" style="margin-top: 12px;">
        {{ spotifyError }}
      </div>
      <div v-if="spotifySuccess" class="alert alert-success" style="margin-top: 12px;">
        {{ spotifySuccess }}
      </div>
    </div>
    
    <!-- Actions Card -->
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">M3U Playlists</h2>
        <div style="display: flex; gap: 12px;">
          <button class="btn btn-secondary" @click="loadPlaylists" :disabled="loading">
            <span v-if="loading" class="spinner"></span>
            Refresh
          </button>
          <button 
            class="btn btn-primary" 
            @click="importSelected" 
            :disabled="!selectedPlaylists.length || importing"
          >
            <span v-if="importing" class="spinner"></span>
            Import {{ selectedPlaylists.length > 0 ? `(${selectedPlaylists.length})` : 'Selected' }}
          </button>
        </div>
      </div>
      
      <!-- Messages -->
      <div v-if="error" class="alert alert-error">
        {{ error }}
      </div>
      <div v-if="successMessage" class="alert alert-success">
        {{ successMessage }}
      </div>
      
      <!-- Search -->
      <div class="search-box">
        <span class="search-icon">🔍</span>
        <input 
          v-model="searchQuery" 
          type="text" 
          class="form-input" 
          placeholder="Search playlists..."
          style="padding-left: 44px;"
        >
      </div>
      
      <!-- Select All -->
      <div style="margin-bottom: 16px; display: flex; align-items: center; gap: 16px;">
        <label class="checkbox">
          <input type="checkbox" v-model="selectAll" @change="toggleSelectAll">
          <span>Select All</span>
        </label>
        <label class="checkbox">
          <input type="checkbox" v-model="overwrite">
          <span>Overwrite existing playlists</span>
        </label>
      </div>
      
      <!-- Playlist List -->
      <div v-if="loading" class="empty-state">
        <div class="spinner" style="width: 40px; height: 40px; margin: 0 auto;"></div>
        <p style="margin-top: 16px;">Loading playlists...</p>
      </div>
      
      <div v-else-if="!filteredPlaylists.length" class="empty-state">
        <img src="/playlist-icon.png" alt="No playlists" class="empty-state-img" />
        <p v-if="searchQuery">No playlists match "{{ searchQuery }}"</p>
        <p v-else>No playlists found. Check your settings.</p>
        <router-link to="/settings" class="btn btn-secondary" style="margin-top: 16px;">
          Go to Settings
        </router-link>
      </div>
      
      <div v-else class="playlist-list">
        <div 
          v-for="playlist in filteredPlaylists" 
          :key="playlist.path"
          class="playlist-item"
          :class="{ selected: isSelected(playlist) }"
          @click="toggleSelect(playlist)"
        >
          <div style="display: flex; align-items: center; gap: 12px;">
            <input 
              type="checkbox" 
              :checked="isSelected(playlist)"
              @click.stop
              @change="toggleSelect(playlist)"
              style="width: 18px; height: 18px; accent-color: var(--accent);"
            >
            <div class="playlist-info">
              <div class="playlist-name">{{ playlist.name }}</div>
              <div class="playlist-meta">{{ playlist.track_count }} tracks</div>
            </div>
          </div>
          <div class="playlist-actions" @click.stop>
            <button class="btn btn-sm btn-secondary" @click="previewPlaylist(playlist)">
              Preview
            </button>
            <button class="btn btn-sm btn-primary" @click="importSingle(playlist)">
              Import
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Preview Modal -->
    <div v-if="previewModal" class="modal-overlay" @click.self="previewModal = null">
      <div class="modal">
        <div class="modal-header">
          <h3 class="modal-title">{{ previewModal.name }}</h3>
          <button class="modal-close" @click="previewModal = null">&times;</button>
        </div>
        <div class="modal-body">
          <div v-if="previewLoading" class="empty-state">
            <div class="spinner" style="width: 40px; height: 40px; margin: 0 auto;"></div>
            <p style="margin-top: 16px;">Loading preview...</p>
          </div>
          
          <div v-else>
            <!-- Match stats -->
            <div style="display: flex; gap: 16px; margin-bottom: 20px;">
              <span class="badge badge-success">
                {{ matchedCount }} matched
              </span>
              <span class="badge badge-error">
                {{ unmatchedCount }} not found
              </span>
            </div>
            
            <!-- Track list -->
            <div class="track-list">
              <div 
                v-for="(track, index) in previewModal.tracks" 
                :key="index"
                class="track-item"
              >
                <div class="track-info">
                  <div class="track-title">
                    {{ track.title || track.filename }}
                  </div>
                  <div class="track-artist" v-if="track.artist">
                    {{ track.artist }}
                  </div>
                  <div class="track-artist" v-if="track.matched && track.plex_title">
                    → {{ track.plex_artist }} - {{ track.plex_title }}
                  </div>
                </div>
                <div class="track-status">
                  <span v-if="track.matched" class="badge badge-success">
                    {{ track.match_type }}
                  </span>
                  <span v-else class="badge badge-error">
                    not found
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="previewModal = null">Close</button>
          <button class="btn btn-primary" @click="importFromPreview">
            Import Playlist
          </button>
        </div>
      </div>
    </div>
    
    <!-- Spotify Preview Modal -->
    <div v-if="spotifyPreview" class="modal-overlay" @click.self="spotifyPreview = null">
      <div class="modal">
        <div class="modal-header">
          <h3 class="modal-title">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="#1DB954" style="vertical-align: middle; margin-right: 8px;">
              <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
            </svg>
            {{ spotifyPreview.name }}
          </h3>
          <button class="modal-close" @click="spotifyPreview = null">&times;</button>
        </div>
        <div class="modal-body">
          <div class="spotify-preview-header">
            <img v-if="spotifyPreview.image_url" :src="spotifyPreview.image_url" class="spotify-cover" />
            <div class="spotify-meta">
              <div v-if="spotifyPreview.owner" class="spotify-owner">by {{ spotifyPreview.owner }}</div>
              <div v-if="spotifyPreview.description" class="spotify-desc">{{ spotifyPreview.description }}</div>
            </div>
          </div>
          
          <!-- Match stats -->
          <div style="display: flex; gap: 16px; margin: 16px 0;">
            <span class="badge badge-success">
              {{ spotifyMatchedCount }} matched
            </span>
            <span class="badge badge-error">
              {{ spotifyUnmatchedCount }} not found
            </span>
          </div>
          
          <!-- Track list -->
          <div class="track-list">
            <div 
              v-for="(track, index) in spotifyPreview.tracks" 
              :key="index"
              class="track-item"
            >
              <div class="track-info">
                <div class="track-title">{{ track.title }}</div>
                <div class="track-artist">{{ track.artist }}</div>
                <div class="track-artist" v-if="track.matched && track.plex_title">
                  → {{ track.plex_artist }} - {{ track.plex_title }}
                </div>
              </div>
              <div class="track-status">
                <span v-if="track.matched" class="badge badge-success">
                  {{ track.match_type }}
                </span>
                <span v-else class="badge badge-error">
                  not found
                </span>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <label class="checkbox" style="margin-right: auto;">
            <input type="checkbox" v-model="spotifyOverwrite">
            <span>Overwrite if exists</span>
          </label>
          <button class="btn btn-secondary" @click="spotifyPreview = null">Cancel</button>
          <button class="btn btn-primary" @click="importSpotify" :disabled="spotifyImporting">
            <span v-if="spotifyImporting" class="spinner"></span>
            Import to Plex
          </button>
        </div>
      </div>
    </div>
    
    <!-- Import Results Modal -->
    <div v-if="importResults" class="modal-overlay" @click.self="importResults = null">
      <div class="modal">
        <div class="modal-header">
          <h3 class="modal-title">Import Results</h3>
          <button class="modal-close" @click="importResults = null">&times;</button>
        </div>
        <div class="modal-body">
          <div style="margin-bottom: 20px;">
            <span class="badge badge-success">{{ importResults.successful }} successful</span>
            <span class="badge badge-error" style="margin-left: 8px;">
              {{ importResults.total - importResults.successful }} failed
            </span>
          </div>
          
          <div class="track-list">
            <div 
              v-for="result in importResults.results" 
              :key="result.playlist_name"
              class="track-item"
            >
              <div class="track-info">
                <div class="track-title">{{ result.playlist_name }}</div>
                <div class="track-artist">
                  {{ result.matched_tracks }}/{{ result.total_tracks }} tracks matched
                </div>
              </div>
              <div class="track-status">
                <span v-if="result.created" class="badge badge-success">created</span>
                <span v-else class="badge badge-error" :title="result.error">failed</span>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-primary" @click="importResults = null">Done</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'Home',
  data() {
    return {
      playlists: [],
      selectedPlaylists: [],
      loading: false,
      importing: false,
      error: '',
      successMessage: '',
      searchQuery: '',
      selectAll: false,
      overwrite: false,
      previewModal: null,
      previewLoading: false,
      importResults: null,
      // Spotify
      spotifyUrl: '',
      spotifyLoading: false,
      spotifyError: '',
      spotifySuccess: '',
      spotifyPreview: null,
      spotifyOverwrite: false,
      spotifyImporting: false
    }
  },
  computed: {
    filteredPlaylists() {
      if (!this.searchQuery) return this.playlists
      const query = this.searchQuery.toLowerCase()
      return this.playlists.filter(p => 
        p.name.toLowerCase().includes(query)
      )
    },
    totalTracks() {
      return this.playlists.reduce((sum, p) => sum + p.track_count, 0)
    },
    matchedCount() {
      if (!this.previewModal?.tracks) return 0
      return this.previewModal.tracks.filter(t => t.matched).length
    },
    unmatchedCount() {
      if (!this.previewModal?.tracks) return 0
      return this.previewModal.tracks.filter(t => !t.matched).length
    },
    spotifyMatchedCount() {
      if (!this.spotifyPreview?.tracks) return 0
      return this.spotifyPreview.tracks.filter(t => t.matched).length
    },
    spotifyUnmatchedCount() {
      if (!this.spotifyPreview?.tracks) return 0
      return this.spotifyPreview.tracks.filter(t => !t.matched).length
    }
  },
  mounted() {
    this.loadPlaylists()
  },
  methods: {
    async loadPlaylists() {
      this.loading = true
      this.error = ''
      this.successMessage = ''
      
      try {
        const { data } = await axios.get('/api/playlists')
        this.playlists = data
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to load playlists'
      }
      
      this.loading = false
    },
    
    isSelected(playlist) {
      return this.selectedPlaylists.some(p => p.path === playlist.path)
    },
    
    toggleSelect(playlist) {
      const index = this.selectedPlaylists.findIndex(p => p.path === playlist.path)
      if (index >= 0) {
        this.selectedPlaylists.splice(index, 1)
      } else {
        this.selectedPlaylists.push(playlist)
      }
      this.selectAll = this.selectedPlaylists.length === this.filteredPlaylists.length
    },
    
    toggleSelectAll() {
      if (this.selectAll) {
        this.selectedPlaylists = [...this.filteredPlaylists]
      } else {
        this.selectedPlaylists = []
      }
    },
    
    async previewPlaylist(playlist) {
      this.previewModal = { ...playlist, tracks: [] }
      this.previewLoading = true
      
      try {
        const { data } = await axios.get('/api/playlists/preview', {
          params: { path: playlist.path }
        })
        this.previewModal = data
      } catch (error) {
        this.previewModal.error = error.response?.data?.detail || 'Failed to load preview'
      }
      
      this.previewLoading = false
    },
    
    async importSingle(playlist) {
      this.importing = true
      this.error = ''
      this.successMessage = ''
      
      try {
        const { data } = await axios.post('/api/playlists/import', {
          playlist_path: playlist.path,
          overwrite: this.overwrite
        })
        this.successMessage = `Created "${data.playlist_name}" with ${data.matched_tracks}/${data.total_tracks} tracks`
      } catch (error) {
        this.error = error.response?.data?.detail || 'Import failed'
      }
      
      this.importing = false
    },
    
    async importFromPreview() {
      if (!this.previewModal) return
      await this.importSingle(this.previewModal)
      this.previewModal = null
    },
    
    async importSelected() {
      if (!this.selectedPlaylists.length) return
      
      this.importing = true
      this.error = ''
      this.successMessage = ''
      
      try {
        const { data } = await axios.post('/api/playlists/import-batch', {
          playlist_paths: this.selectedPlaylists.map(p => p.path),
          overwrite: this.overwrite
        })
        
        this.importResults = data
        this.selectedPlaylists = []
        this.selectAll = false
      } catch (error) {
        this.error = error.response?.data?.detail || 'Batch import failed'
      }
      
      this.importing = false
    },
    
    // Spotify methods
    async previewSpotify() {
      if (!this.spotifyUrl) return
      
      this.spotifyLoading = true
      this.spotifyError = ''
      this.spotifySuccess = ''
      
      try {
        const { data } = await axios.post('/api/spotify/preview', {
          url: this.spotifyUrl
        })
        this.spotifyPreview = data
      } catch (error) {
        this.spotifyError = error.response?.data?.detail || 'Failed to load Spotify playlist'
      }
      
      this.spotifyLoading = false
    },
    
    async importSpotify() {
      if (!this.spotifyPreview) return
      
      this.spotifyImporting = true
      
      try {
        const { data } = await axios.post('/api/spotify/import', {
          url: this.spotifyUrl,
          overwrite: this.spotifyOverwrite
        })
        
        this.spotifyPreview = null
        this.spotifyUrl = ''
        this.spotifySuccess = `Created "${data.playlist_name}" with ${data.matched_tracks}/${data.total_tracks} tracks`
        
        // Clear success message after 5 seconds
        setTimeout(() => {
          this.spotifySuccess = ''
        }, 5000)
      } catch (error) {
        this.spotifyError = error.response?.data?.detail || 'Import failed'
      }
      
      this.spotifyImporting = false
    }
  }
}
</script>

<style scoped>
/* Hero Section */
.hero-section {
  display: flex;
  align-items: center;
  gap: 32px;
  margin-bottom: 24px;
}

.hero-icon {
  width: auto;
  height: 130px;
  object-fit: contain;
  border-radius: 50%;
  filter: drop-shadow(0 8px 24px rgba(100, 120, 180, 0.4));
  animation: float 4s ease-in-out infinite, glow 2s ease-in-out infinite alternate;
}

@keyframes float {
  0%, 100% {
    transform: translateY(0px) rotate(0deg);
  }
  50% {
    transform: translateY(-10px) rotate(2deg);
  }
}

@keyframes glow {
  0% {
    filter: drop-shadow(0 8px 24px rgba(100, 120, 180, 0.4));
  }
  100% {
    filter: drop-shadow(0 8px 32px rgba(100, 120, 180, 0.7));
  }
}

.hero-section .stats {
  flex: 1;
  display: flex;
  gap: 24px;
  margin-bottom: 0;
}

/* Empty State */
.empty-state-img {
  width: 140px;
  height: 140px;
  margin-bottom: 20px;
  opacity: 0.6;
  filter: grayscale(30%);
  animation: pulse 3s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 0.6;
  }
  50% {
    transform: scale(1.05);
    opacity: 0.8;
  }
}

/* Spotify Card */
.spotify-card {
  background: linear-gradient(135deg, rgba(29, 185, 84, 0.1) 0%, rgba(0, 0, 0, 0) 50%);
  border: 1px solid rgba(29, 185, 84, 0.3);
}

.spotify-input-row {
  display: flex;
  gap: 12px;
}

.spotify-input-row .form-input {
  flex: 1;
}

.spotify-preview-header {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.spotify-cover {
  width: 120px;
  height: 120px;
  border-radius: 8px;
  object-fit: cover;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.spotify-meta {
  flex: 1;
}

.spotify-owner {
  color: var(--text-secondary);
  font-size: 14px;
  margin-bottom: 8px;
}

.spotify-desc {
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.4;
  max-height: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Responsive */
@media (max-width: 768px) {
  .hero-section {
    flex-direction: column;
    text-align: center;
  }
  
  .hero-icon {
    width: 100px;
    height: 100px;
  }
  
  .hero-section .stats {
    flex-direction: column;
    gap: 12px;
    width: 100%;
  }
  
  .spotify-input-row {
    flex-direction: column;
  }
  
  .spotify-preview-header {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }
}
</style>
