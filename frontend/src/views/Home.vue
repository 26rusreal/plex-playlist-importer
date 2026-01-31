<template>
  <div class="home">
    <!-- Stats -->
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
        <div class="empty-state-icon">📂</div>
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
      importResults: null
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
    }
  }
}
</script>
