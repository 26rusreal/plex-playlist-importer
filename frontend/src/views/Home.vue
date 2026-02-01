<template>
  <div class="home">
    <!-- Hero Section with Icon -->
    <div class="hero-section">
      <img src="/playlist-icon.svg" alt="Playlist Icon" class="hero-icon" />
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
        <img src="/playlist-icon.svg" alt="No playlists" class="empty-state-img" />
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

    <!-- Import Progress Modal -->
    <div v-if="importProgress" class="modal-overlay" @click.self="closeImportProgress">
      <div class="modal import-progress-modal">
        <div class="modal-header">
          <h3 class="modal-title">Импорт: {{ importProgress.playlistName }}</h3>
          <button
            v-if="importProgress.status !== 'running'"
            class="modal-close"
            @click="closeImportProgress"
          >
            &times;
          </button>
        </div>
        <div class="modal-body">
          <div class="import-progress-summary">
            <div class="progress-bar">
              <div class="progress-bar-fill" :style="{ width: `${importProgressPercent}%` }"></div>
            </div>
            <div class="progress-meta">
              <span v-if="importProgress.status === 'running'">Добавление треков...</span>
              <span v-else-if="importProgress.status === 'done'">Импорт завершен</span>
              <span v-else>Импорт завершился ошибкой</span>
              <span>{{ importProgress.processed }}/{{ importProgress.total }}</span>
            </div>
          </div>

          <div v-if="!importProgress.tracks.length" class="empty-state">
            <div class="spinner" style="width: 40px; height: 40px; margin: 0 auto;"></div>
            <p style="margin-top: 16px;">Загружаем список треков...</p>
          </div>

          <div v-else class="track-list">
            <div
              v-for="(track, index) in importProgress.tracks"
              :key="index"
              class="track-item import-track-item"
              :class="{ active: importProgress.status === 'running' && importProgress.activeIndex === index }"
            >
              <div class="track-info">
                <div class="track-title">
                  {{ track.title || track.filename || track.plex_title || 'Неизвестный трек' }}
                </div>
                <div class="track-artist" v-if="track.artist">
                  {{ track.artist }}
                </div>
                <div class="track-artist" v-else-if="track.plex_artist">
                  {{ track.plex_artist }}
                </div>
              </div>
              <div class="track-status">
                <span v-if="track.status === 'added'" class="badge badge-success">
                  добавлен
                </span>
                <span v-else-if="track.status === 'skipped'" class="badge badge-error">
                  не найден
                </span>
                <span v-else-if="track.status === 'error'" class="badge badge-error">
                  ошибка
                </span>
                <span v-else class="badge badge-info">
                  в очереди
                </span>
              </div>
            </div>
          </div>

          <div v-if="importProgress.message" class="alert alert-error" style="margin-top: 16px;">
            {{ importProgress.message }}
          </div>
        </div>
        <div class="modal-footer">
          <button v-if="importProgress.status !== 'running'" class="btn btn-primary" @click="closeImportProgress">
            Готово
          </button>
          <button v-else class="btn btn-secondary" disabled>
            Импортируем...
          </button>
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
      importProgress: null,
      importProgressTimer: null
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
    importProgressPercent() {
      if (!this.importProgress?.total) return 0
      return Math.round((this.importProgress.processed / this.importProgress.total) * 100)
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
      const result = await this.importPlaylistWithVisualization(playlist)
      if (result?.created) {
        this.successMessage = `Created "${result.playlist_name}" with ${result.matched_tracks}/${result.total_tracks} tracks`
      }
    },
    
    async importFromPreview() {
      if (!this.previewModal) return
      const tracks = this.previewModal.tracks || []
      const result = await this.importPlaylistWithVisualization(this.previewModal, { tracks })
      if (result?.created) {
        this.successMessage = `Created "${result.playlist_name}" with ${result.matched_tracks}/${result.total_tracks} tracks`
      }
      this.previewModal = null
    },
    
    async importSelected() {
      if (!this.selectedPlaylists.length) return
      this.importing = true
      this.error = ''
      this.successMessage = ''
      this.importResults = null

      const results = []
      for (const playlist of this.selectedPlaylists) {
        const result = await this.importPlaylistWithVisualization(playlist, { showMessages: false })
        if (result) {
          results.push(result)
        }
      }

      this.importResults = {
        results,
        total: results.length,
        successful: results.filter(result => result.created).length
      }
      this.selectedPlaylists = []
      this.selectAll = false
      this.importing = false
    },

    async importPlaylistWithVisualization(playlist, { tracks = [], showMessages = true } = {}) {
      this.importing = true
      if (showMessages) {
        this.error = ''
        this.successMessage = ''
      }

      this.startImportProgress(playlist.name, tracks)

      const previewPromise = tracks.length ? null : this.fetchPreviewTracks(playlist)
      const importPromise = axios.post('/api/playlists/import', {
        playlist_path: playlist.path,
        overwrite: this.overwrite
      })

      if (previewPromise) {
        const previewTracks = await previewPromise
        if (previewTracks.length) {
          this.updateImportTracks(previewTracks)
        }
      }

      try {
        const { data } = await importPromise
        const matches = data.matches || this.importProgress?.tracks || []
        await this.revealImportMatches(matches)
        this.importProgress.status = 'done'
        return data
      } catch (error) {
        const message = error.response?.data?.detail || 'Import failed'
        this.importProgress.status = 'error'
        this.importProgress.message = message
        this.markImportTracksError()
        if (showMessages) {
          this.error = message
        }
        return {
          playlist_name: playlist.name,
          total_tracks: this.importProgress?.total || playlist.track_count || 0,
          matched_tracks: 0,
          created: false,
          error: message
        }
      } finally {
        this.importing = false
      }
    },

    startImportProgress(playlistName, tracks) {
      this.importProgress = {
        playlistName,
        tracks: tracks.map(track => ({ ...track, status: 'pending' })),
        processed: 0,
        total: tracks.length,
        status: 'running',
        activeIndex: 0,
        message: ''
      }
      this.startImportProgressTicker()
    },

    startImportProgressTicker() {
      this.stopImportProgressTicker()
      if (!this.importProgress?.tracks.length) return
      this.importProgressTimer = setInterval(() => {
        if (!this.importProgress || this.importProgress.status !== 'running') return
        const nextIndex = (this.importProgress.activeIndex + 1) % this.importProgress.tracks.length
        this.importProgress.activeIndex = nextIndex
      }, 450)
    },

    stopImportProgressTicker() {
      if (this.importProgressTimer) {
        clearInterval(this.importProgressTimer)
        this.importProgressTimer = null
      }
    },

    updateImportTracks(tracks) {
      if (!this.importProgress) return
      this.importProgress.tracks = tracks.map(track => ({ ...track, status: 'pending' }))
      this.importProgress.total = tracks.length
      this.importProgress.processed = 0
      this.importProgress.activeIndex = 0
      this.startImportProgressTicker()
    },

    async fetchPreviewTracks(playlist) {
      try {
        const { data } = await axios.get('/api/playlists/preview', {
          params: { path: playlist.path }
        })
        return data.tracks || []
      } catch (error) {
        return []
      }
    },

    async revealImportMatches(matches) {
      if (!this.importProgress) return
      this.stopImportProgressTicker()
      const preparedMatches = matches.map(match => ({
        ...match,
        status: match.matched ? 'added' : 'skipped'
      }))

      if (!preparedMatches.length) {
        this.importProgress.processed = 0
        this.importProgress.total = 0
        return
      }

      this.importProgress.tracks = preparedMatches.map(match => ({ ...match, status: 'pending' }))
      this.importProgress.total = preparedMatches.length
      this.importProgress.processed = 0

      for (let index = 0; index < preparedMatches.length; index += 1) {
        this.importProgress.activeIndex = index
        this.importProgress.tracks.splice(index, 1, preparedMatches[index])
        this.importProgress.processed = index + 1
        await this.wait(70)
      }
    },

    markImportTracksError() {
      if (!this.importProgress?.tracks.length) return
      this.stopImportProgressTicker()
      this.importProgress.tracks = this.importProgress.tracks.map(track => ({
        ...track,
        status: 'error'
      }))
    },

    closeImportProgress() {
      if (this.importProgress?.status === 'running') return
      this.stopImportProgressTicker()
      this.importProgress = null
    },

    wait(delay) {
      return new Promise(resolve => setTimeout(resolve, delay))
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

.import-progress-modal {
  max-width: 720px;
}

.import-progress-summary {
  margin-bottom: 20px;
}

.progress-bar {
  width: 100%;
  height: 10px;
  background: var(--border);
  border-radius: 999px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent), #7ab8ff);
  transition: width 0.3s ease;
}

.progress-meta {
  margin-top: 10px;
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: var(--text-secondary);
}

.import-track-item.active {
  background: rgba(122, 184, 255, 0.15);
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
}
</style>
