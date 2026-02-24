<template>
  <div class="home">
    <!-- Hero Section with Icon -->
    <div class="hero-section hero-reveal">
      <img src="/playlist-icon.svg" alt="Playlist Icon" class="hero-icon" />
      <div class="stats">
        <div class="stat-item stat-reveal" style="animation-delay: 0.1s">
          <div class="stat-value">{{ playlists.length }}</div>
          <div class="stat-label">Playlists Found</div>
        </div>
        <div class="stat-item stat-reveal" style="animation-delay: 0.18s">
          <div class="stat-value">{{ totalTracks }}</div>
          <div class="stat-label">Total Tracks</div>
        </div>
        <div class="stat-item stat-reveal" style="animation-delay: 0.26s">
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
      
      <div v-if="!spotifyConfigured" class="spotify-setup-hint">
        <span>⚠️</span> Spotify not configured. 
        <router-link to="/settings">Add credentials in Settings</router-link>
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
      
      <!-- Toolbar: search + view -->
      <div class="playlist-toolbar">
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
        <div class="toolbar-options">
          <label class="checkbox">
            <input type="checkbox" v-model="overwrite">
            <span>Overwrite existing</span>
          </label>
          <button 
            type="button" 
            class="btn btn-sm btn-secondary" 
            aria-label="Expand all groups"
            @click="expandAllGroups(true)"
          >
            Expand all
          </button>
          <button 
            type="button" 
            class="btn btn-sm btn-secondary" 
            aria-label="Collapse all groups"
            @click="expandAllGroups(false)"
          >
            Collapse all
          </button>
        </div>
      </div>
      
      <!-- Select All (above groups) -->
      <div class="select-all-row">
        <label class="checkbox">
          <input type="checkbox" v-model="selectAll" @change="toggleSelectAll">
          <span>Select all visible</span>
        </label>
      </div>
      
      <!-- Playlist List by Group -->
      <div v-if="loading" class="empty-state">
        <div class="spinner" style="width: 40px; height: 40px; margin: 0 auto;"></div>
        <p style="margin-top: 16px;">Scanning music folder recursively...</p>
      </div>
      
      <div v-else-if="!filteredPlaylists.length" class="empty-state">
        <img src="/playlist-icon.svg" alt="No playlists" class="empty-state-img" />
        <p v-if="searchQuery">No playlists match "{{ searchQuery }}"</p>
        <p v-else>No playlists found. Mount music root in Settings.</p>
        <router-link to="/settings" class="btn btn-secondary" style="margin-top: 16px;">
          Settings
        </router-link>
      </div>
      
      <div v-else class="playlist-groups">
        <div 
          v-for="(items, groupName) in playlistsByGroup" 
          :key="groupName"
          class="playlist-group"
        >
          <button 
            type="button"
            class="group-header"
            :class="{ expanded: expandedGroups[groupName] }"
            :aria-expanded="expandedGroups[groupName]"
            :aria-label="`Toggle ${groupName}, ${items.length} playlists`"
            @click="toggleGroup(groupName)"
          >
            <span class="group-arrow" aria-hidden="true">{{ expandedGroups[groupName] ? '▼' : '▶' }}</span>
            <span class="group-name">{{ groupName }}</span>
            <span class="group-count">{{ items.length }} playlists</span>
          </button>
          <div v-show="expandedGroups[groupName]" class="group-content">
            <div 
              v-for="playlist in items" 
              :key="playlist.path"
              class="playlist-item"
              :class="{ selected: isSelected(playlist) }"
              @click="toggleSelect(playlist)"
            >
              <div class="playlist-item-inner">
                <input 
                  type="checkbox" 
                  :checked="isSelected(playlist)"
                  :aria-label="`Select playlist ${playlist.name}`"
                  @click.stop
                  @change="toggleSelect(playlist)"
                  class="playlist-checkbox"
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
      </div>
    </div>
    
    <!-- Preview Modal -->
    <div v-if="previewModal" class="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="preview-modal-title" @click.self="previewModal = null">
      <div class="modal">
        <div class="modal-header">
          <h3 id="preview-modal-title" class="modal-title">{{ previewModal.name }}</h3>
          <button type="button" class="modal-close" aria-label="Close" @click="previewModal = null">&times;</button>
        </div>
        <div class="modal-body">
          <div v-if="previewLoading" class="empty-state">
            <div class="spinner" style="width: 40px; height: 40px; margin: 0 auto;"></div>
            <p style="margin-top: 16px;">Loading preview...</p>
          </div>
          
          <div v-else>
            <div v-if="!(previewModal.tracks && previewModal.tracks.length)" class="empty-state" style="margin: 16px 0;">
              <p>No track data received (tracks: {{ previewModal.tracks == null ? 'null' : (previewModal.tracks && previewModal.tracks.length) || 0 }})</p>
            </div>
            <template v-else>
            <!-- Match stats -->
            <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 20px;">
              <span class="status-icon status-icon--success" aria-label="Matched"></span>
              <span>{{ matchedCount }}</span>
              <span class="status-icon status-icon--error" aria-label="Not found"></span>
              <span>{{ unmatchedCount }}</span>
            </div>
            
            <!-- Track list -->
            <div class="track-list">
              <div 
                v-for="(track, index) in (previewModal.tracks || [])" 
                :key="track.filename || index"
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
                  <span v-if="track.matched" class="status-icon status-icon--success" aria-label="Matched"></span>
                  <template v-else>
                    <span class="status-icon status-icon--error" aria-label="Not found"></span>
                    <button 
                      v-if="slskdEnabled" 
                      class="btn btn-xs btn-slskd" 
                      @click="searchSlskd(track)"
                      :disabled="track.slskdSearching"
                    >
                      <span v-if="track.slskdSearching" class="spinner-xs"></span>
                      {{ track.slskdSearching ? '' : '🎵' }}
                    </button>
                  </template>
                </div>
              </div>
            </div>
            </template>
          </div>
        </div>
        <div v-if="importingFromPreview" class="spinner-dots-wrap" aria-hidden="true">
          <div class="spinner-dots spinner-dots--spin">
            <span class="spinner-dot"></span><span class="spinner-dot"></span><span class="spinner-dot"></span><span class="spinner-dot"></span><span class="spinner-dot"></span><span class="spinner-dot"></span><span class="spinner-dot"></span><span class="spinner-dot"></span>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="previewModal = null" :disabled="importingFromPreview">Close</button>
          <button class="btn btn-primary" @click="importFromPreview" :disabled="importingFromPreview">
            <span v-if="importingFromPreview" class="spinner" style="width: 16px; height: 16px; margin-right: 8px;"></span>
            {{ importingFromPreview ? 'Importing…' : 'Import Playlist' }}
          </button>
        </div>
        <div v-if="previewImportError" class="alert alert-error" style="margin: 0 24px 16px;">
          {{ previewImportError }}
        </div>
      </div>
    </div>
    
    <!-- Spotify Preview Modal -->
    <div v-if="spotifyPreview" class="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="spotify-modal-title" @click.self="spotifyPreview = null">
      <div class="modal">
        <div class="modal-header">
          <h3 id="spotify-modal-title" class="modal-title">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="#1DB954" style="vertical-align: middle; margin-right: 8px;" aria-hidden="true">
              <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
            </svg>
            {{ spotifyPreview.name }}
          </h3>
          <button type="button" class="modal-close" aria-label="Close" @click="spotifyPreview = null">&times;</button>
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
          <div style="display: flex; align-items: center; gap: 16px; margin: 16px 0;">
            <span class="status-icon status-icon--success" aria-label="Matched"></span>
            <span>{{ spotifyMatchedCount }}</span>
            <span class="status-icon status-icon--error" aria-label="Not found"></span>
            <span>{{ spotifyUnmatchedCount }}</span>
          </div>
          
          <!-- Track list -->
          <div class="track-list">
            <div 
              v-for="(track, index) in spotifyPreview.tracks" 
              :key="track.id || `${track.artist}-${track.title}-${index}`"
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
                <span v-if="track.matched" class="status-icon status-icon--success" aria-label="Matched"></span>
                <template v-else>
                  <span class="status-icon status-icon--error" aria-label="Not found"></span>
                  <button 
                    v-if="slskdEnabled" 
                    class="btn btn-xs btn-slskd" 
                    @click="searchSlskd(track)"
                    :disabled="track.slskdSearching"
                    title="Search in Soulseek"
                    aria-label="Search in Soulseek"
                  >
                    <span v-if="track.slskdSearching" class="spinner-xs"></span>
                    <span v-else aria-hidden="true">🎵</span>
                  </button>
                </template>
              </div>
            </div>
          </div>
        </div>
        <div v-if="spotifyImporting" class="spinner-dots-wrap" aria-hidden="true">
          <div class="spinner-dots spinner-dots--spin">
            <span class="spinner-dot"></span><span class="spinner-dot"></span><span class="spinner-dot"></span><span class="spinner-dot"></span><span class="spinner-dot"></span><span class="spinner-dot"></span><span class="spinner-dot"></span><span class="spinner-dot"></span>
          </div>
        </div>
        <div class="modal-footer">
          <label class="checkbox" style="margin-right: auto;">
            <input type="checkbox" v-model="spotifyOverwrite">
            <span>Overwrite if exists</span>
          </label>
          <button class="btn btn-secondary" @click="spotifyPreview = null" :disabled="spotifyImporting">Cancel</button>
          <button class="btn btn-primary" @click="importSpotify" :disabled="spotifyImporting">
            <span v-if="spotifyImporting" class="spinner" style="width: 16px; height: 16px; margin-right: 8px;"></span>
            {{ spotifyImporting ? 'Importing…' : 'Import to Plex' }}
          </button>
        </div>
        <div v-if="spotifyImportError" class="alert alert-error" style="margin: 0 24px 16px;">
          {{ spotifyImportError }}
        </div>
      </div>
    </div>
    
    <!-- Import Results Modal -->
    <div v-if="importResults" class="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="import-results-title" @click.self="importResults = null">
      <div class="modal">
        <div class="modal-header">
          <h3 id="import-results-title" class="modal-title">Import Results</h3>
          <button type="button" class="modal-close" aria-label="Close" @click="importResults = null">&times;</button>
        </div>
        <div class="modal-body">
          <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 20px;">
            <span class="status-icon status-icon--success" aria-label="Successful"></span>
            <span>{{ importResults.successful }}</span>
            <span class="status-icon status-icon--error" aria-label="Failed"></span>
            <span>{{ importResults.total - importResults.successful }}</span>
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
                <span v-if="result.created" class="status-icon status-icon--success" aria-label="Created"></span>
                <span v-else class="status-icon status-icon--error" :title="result.error" aria-label="Failed"></span>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-primary" @click="importResults = null">Done</button>
        </div>
      </div>
    </div>
    
    <!-- SLSKD Search Modal -->
    <div v-if="slskdModal" class="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="slskd-modal-title" @click.self="slskdModal = null">
      <div class="modal">
        <div class="modal-header">
          <h3 id="slskd-modal-title" class="modal-title">
            <span aria-hidden="true">🎵</span> Soulseek Search
          </h3>
          <button type="button" class="modal-close" aria-label="Close" @click="slskdModal = null">&times;</button>
        </div>
        <div class="modal-body">
          <div class="slskd-search-info">
            <strong>{{ slskdModal.track?.artist }} - {{ slskdModal.track?.title }}</strong>
          </div>
          
          <div v-if="slskdModal.loading" class="empty-state">
            <div class="spinner" style="width: 40px; height: 40px; margin: 0 auto;"></div>
            <p style="margin-top: 16px;">Searching Soulseek network...</p>
          </div>
          
          <div v-else-if="slskdModal.error" class="alert alert-error">
            {{ slskdModal.error }}
          </div>
          
          <div v-else-if="slskdModal.results && slskdModal.results.length > 0">
            <div style="margin-bottom: 12px; color: var(--text-secondary);">
              Found {{ slskdModal.results.length }} results
            </div>
            
            <div class="slskd-results">
              <div 
                v-for="(file, index) in slskdModal.results.slice(0, 20)" 
                :key="`${file.filename}-${file.username}-${file.size || index}`"
                class="slskd-file"
                :class="{ selected: slskdModal.selectedFile === index }"
                @click="slskdModal.selectedFile = index"
              >
                <div class="slskd-file-info">
                  <div class="slskd-filename">{{ getFilename(file.filename) }}</div>
                  <div class="slskd-meta">
                    <span class="slskd-ext">{{ file.extension.toUpperCase() }}</span>
                    <span v-if="file.bit_rate">{{ file.bit_rate }} kbps</span>
                    <span>{{ formatSize(file.size) }}</span>
                    <span class="slskd-user">@{{ file.username }}</span>
                  </div>
                </div>
                <div v-if="slskdModal.selectedFile === index" class="slskd-check">✓</div>
              </div>
            </div>
          </div>
          
          <div v-else class="empty-state">
            <p>No results found</p>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="slskdModal = null">Cancel</button>
          <button 
            class="btn btn-slskd" 
            @click="downloadSlskdFile" 
            :disabled="slskdModal.selectedFile === null || slskdModal.downloading"
          >
            <span v-if="slskdModal.downloading" class="spinner"></span>
            {{ slskdModal.downloading ? 'Queueing...' : 'Download Selected' }}
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
      importingFromPreview: false,
      previewImportError: '',
      importResults: null,
      // Spotify
      spotifyUrl: '',
      spotifyLoading: false,
      spotifyError: '',
      spotifySuccess: '',
      spotifyPreview: null,
      spotifyOverwrite: false,
      spotifyImporting: false,
      spotifyImportError: '',
      spotifyConfigured: true, // assume configured until check
      // SLSKD
      slskdEnabled: false,
      slskdModal: null,
      // Groups (folder names) expanded state
      expandedGroups: {}
    }
  },
  computed: {
    filteredPlaylists() {
      const list = this.playlists || []
      if (!this.searchQuery) return list
      const query = this.searchQuery.toLowerCase()
      return list.filter(p =>
        (p && p.name && p.name.toLowerCase().includes(query)) ||
        (p && p.group && p.group.toLowerCase().includes(query))
      )
    },
    playlistsByGroup() {
      const list = this.filteredPlaylists || []
      const map = {}
      for (const p of list) {
        const g = p.group || 'Root'
        if (!map[g]) map[g] = []
        map[g].push(p)
      }
      const sorted = {}
      const keys = Object.keys(map).sort((a, b) => a.localeCompare(b))
      keys.forEach(k => { sorted[k] = map[k] })
      return sorted
    },
    totalTracks() {
      return (this.playlists || []).reduce((sum, p) => sum + (p && p.track_count || 0), 0)
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
    this.checkSpotifyStatus()
    this.checkSlskdStatus()
    window.addEventListener('keydown', this.onEscapeKey)
  },
  beforeUnmount() {
    window.removeEventListener('keydown', this.onEscapeKey)
  },
  methods: {
    onEscapeKey(e) {
      if (e.key !== 'Escape') return
      if (this.slskdModal) { this.slskdModal = null; e.preventDefault(); return }
      if (this.importResults) { this.importResults = null; e.preventDefault(); return }
      if (this.spotifyPreview) { this.spotifyPreview = null; e.preventDefault(); return }
      if (this.previewModal) { this.previewModal = null; e.preventDefault() }
    },
    async checkSpotifyStatus() {
      try {
        const { data } = await axios.get('/api/spotify/status')
        this.spotifyConfigured = data.configured
      } catch (error) {
        this.spotifyConfigured = false
      }
    },
    
    async loadPlaylists() {
      this.loading = true
      this.error = ''
      this.successMessage = ''
      
      try {
        const { data } = await axios.get('/api/playlists')
        this.playlists = Array.isArray(data) ? data : []
        const groups = {}
        const seen = new Set()
        for (const p of this.playlists) {
          const g = p.group || 'Root'
          if (!seen.has(g)) {
            seen.add(g)
            groups[g] = true
          }
        }
        this.expandedGroups = { ...this.expandedGroups, ...groups }
      } catch (error) {
        this.error = error.response?.data?.detail || 'Failed to load playlists'
      }
      
      this.loading = false
    },
    toggleGroup(groupName) {
      this.expandedGroups = { ...this.expandedGroups, [groupName]: !this.expandedGroups[groupName] }
    },
    expandAllGroups(open) {
      const next = {}
      for (const g of Object.keys(this.playlistsByGroup)) {
        next[g] = open
      }
      this.expandedGroups = { ...this.expandedGroups, ...next }
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
      // #region agent log
      fetch('http://localhost:1558/ingest/267a81b1-3061-4444-83dc-5d64e46c6e08',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'459f84'},body:JSON.stringify({sessionId:'459f84',hypothesisId:'H1',location:'Home.vue:previewPlaylist',message:'preview requested',data:{path:playlist.path},timestamp:Date.now()})}).catch(()=>{});
      // #endregion
      try {
        const { data } = await axios.get('/api/playlists/preview', {
          params: { path: playlist.path }
        })
        // #region agent log
        const _logData = { keys: Object.keys(data || {}), hasTracks: !!(data && data.tracks), tracksIsArray: Array.isArray(data && data.tracks), tracksLen: (data && data.tracks) ? data.tracks.length : 0 }
        fetch('http://localhost:1558/ingest/267a81b1-3061-4444-83dc-5d64e46c6e08',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'459f84'},body:JSON.stringify({sessionId:'459f84',hypothesisId:'H1',location:'Home.vue:previewPlaylist:afterGet',message:'preview response',data:_logData,timestamp:Date.now()})}).catch(()=>{});
        try { console.error('[preview debug]', _logData) } catch (_) {}
        // #endregion
        this.previewModal = data
      } catch (error) {
        try { console.error('[preview error]', error) } catch (_) {}
        this.previewModal.error = error.response?.data?.detail || 'Failed to load preview'
        // #region agent log
        fetch('http://localhost:1558/ingest/267a81b1-3061-4444-83dc-5d64e46c6e08',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'459f84'},body:JSON.stringify({sessionId:'459f84',hypothesisId:'H2',location:'Home.vue:previewPlaylist:catch',message:'preview error',data:{detail:error.response&&error.response.data&&error.response.data.detail},timestamp:Date.now()})}).catch(()=>{});
        // #endregion
      }
      this.previewLoading = false
    },
    
    async importSingle(playlist, fromPreview = false) {
      const flag = fromPreview ? 'importingFromPreview' : 'importing'
      this[flag] = true
      if (!fromPreview) {
        this.error = ''
        this.successMessage = ''
      } else {
        this.previewImportError = ''
      }
      try {
        const { data } = await axios.post('/api/playlists/import', {
          playlist_path: playlist.path,
          overwrite: this.overwrite
        })
        this.successMessage = `Created "${data.playlist_name}" with ${data.matched_tracks}/${data.total_tracks} tracks`
        if (fromPreview) return { success: true }
      } catch (error) {
        const msg = error.response?.data?.detail || 'Import failed'
        if (fromPreview) this.previewImportError = msg
        else this.error = msg
        if (fromPreview) return { success: false }
      } finally {
        this[flag] = false
      }
    },
    
    async importFromPreview() {
      if (!this.previewModal) return
      this.importingFromPreview = true
      this.previewImportError = ''
      const result = await this.importSingle(this.previewModal, true)
      if (result && result.success) this.previewModal = null
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
      this.spotifyImportError = ''
      
      try {
        const { data } = await axios.post('/api/spotify/import', {
          url: this.spotifyUrl,
          overwrite: this.spotifyOverwrite
        })
        
        this.spotifyPreview = null
        this.spotifyUrl = ''
        this.spotifySuccess = `Created "${data.playlist_name}" with ${data.matched_tracks}/${data.total_tracks} tracks`
        
        setTimeout(() => { this.spotifySuccess = '' }, 5000)
      } catch (error) {
        const msg = error.response?.data?.detail || 'Import failed'
        this.spotifyImportError = msg
        this.spotifyError = msg
      }
      
      this.spotifyImporting = false
    },
    
    // SLSKD methods
    async checkSlskdStatus() {
      try {
        const { data } = await axios.get('/api/slskd/status')
        this.slskdEnabled = data.enabled
      } catch (error) {
        this.slskdEnabled = false
      }
    },
    
    async searchSlskd(track) {
      // Mark track as searching
      track.slskdSearching = true
      
      // Open modal
      this.slskdModal = {
        track: track,
        loading: true,
        error: null,
        results: [],
        selectedFile: null,
        downloading: false
      }
      
      try {
        const { data } = await axios.post('/api/slskd/search', {
          query: `${track.artist || ''} ${track.title || ''}`.trim(),
          artist: track.artist,
          title: track.title
        })
        
        this.slskdModal.results = data.files || []
        this.slskdModal.loading = false
        
        // Auto-select first result
        if (this.slskdModal.results.length > 0) {
          this.slskdModal.selectedFile = 0
        }
      } catch (error) {
        this.slskdModal.loading = false
        this.slskdModal.error = error.response?.data?.detail || 'Search failed'
      }
      
      track.slskdSearching = false
    },
    
    async downloadSlskdFile() {
      if (!this.slskdModal || this.slskdModal.selectedFile === null) return
      
      const file = this.slskdModal.results[this.slskdModal.selectedFile]
      if (!file) return
      
      this.slskdModal.downloading = true
      
      try {
        await axios.post('/api/slskd/queue', {
          files: [{
            username: file.username,
            filename: file.filename,
            size: file.size
          }]
        })
        
        // Success - close modal
        this.slskdModal = null
        this.successMessage = `Queued download: ${this.getFilename(file.filename)}`
        
        setTimeout(() => {
          this.successMessage = ''
        }, 5000)
      } catch (error) {
        this.slskdModal.downloading = false
        this.slskdModal.error = error.response?.data?.detail || 'Failed to queue download'
      }
    },
    
    getFilename(path) {
      return path.split(/[\\/]/).pop() || path
    },
    
    formatSize(bytes) {
      if (!bytes) return ''
      const mb = bytes / (1024 * 1024)
      return mb.toFixed(1) + ' MB'
    }
  }
}
</script>

<style scoped>
/* Hero Section */
.hero-reveal {
  animation: heroReveal 0.6s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

.stat-reveal {
  opacity: 0;
  animation: statReveal 0.5s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

@keyframes heroReveal {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes statReveal {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

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

.spotify-setup-hint {
  margin-top: 12px;
  padding: 12px;
  background: rgba(229, 160, 13, 0.1);
  border: 1px solid rgba(229, 160, 13, 0.3);
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 14px;
}

.spotify-setup-hint a {
  color: var(--accent);
  text-decoration: none;
}

.spotify-setup-hint a:hover {
  text-decoration: underline;
}

/* Playlist toolbar & groups */
.playlist-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.playlist-toolbar .search-box {
  flex: 1;
  min-width: 200px;
}

.toolbar-options {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.select-all-row {
  margin-bottom: 12px;
}

.playlist-groups {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.playlist-group {
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
  background: var(--bg-secondary);
}

.group-header {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-hover);
  border: none;
  cursor: pointer;
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 600;
  text-align: left;
  transition: background 0.2s;
}

.group-header:hover {
  background: var(--bg-tertiary, rgba(255,255,255,0.06));
}

.group-header .group-arrow {
  font-size: 12px;
  color: var(--text-secondary);
  width: 20px;
}

.group-header .group-name {
  flex: 1;
}

.group-header .group-count {
  font-size: 13px;
  font-weight: 400;
  color: var(--text-secondary);
}

.group-content {
  padding: 4px 0;
}

.playlist-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  cursor: pointer;
  transition: background 0.2s;
  border-bottom: 1px solid var(--border);
}

.playlist-item:last-child {
  border-bottom: none;
}

.playlist-item:hover {
  background: var(--bg-hover);
}

.playlist-item.selected {
  background: rgba(229, 160, 13, 0.12);
}

.playlist-item-inner {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.playlist-checkbox {
  width: 18px;
  height: 18px;
  accent-color: var(--accent);
  flex-shrink: 0;
}

.playlist-info {
  min-width: 0;
}

.playlist-name {
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.playlist-meta {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.playlist-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
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

  .playlist-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .playlist-item {
    flex-wrap: wrap;
    gap: 8px;
  }

  .playlist-actions {
    width: 100%;
    justify-content: flex-end;
    padding-left: 46px;
  }
}

/* SLSKD Styles */
.btn-xs {
  padding: 2px 6px;
  font-size: 11px;
  min-width: auto;
}

.btn-slskd {
  background: #6495ED;
  color: #fff;
}

.btn-slskd:hover:not(:disabled) {
  background: #7ba3f0;
}

.spinner-xs {
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.slskd-search-info {
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: 8px;
  margin-bottom: 16px;
}

.slskd-results {
  max-height: 400px;
  overflow-y: auto;
}

.slskd-file {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  border: 2px solid transparent;
  transition: all 0.2s;
}

.slskd-file:hover {
  background: var(--bg-hover);
}

.slskd-file.selected {
  border-color: #6495ED;
  background: rgba(100, 149, 237, 0.1);
}

.slskd-file-info {
  flex: 1;
  min-width: 0;
}

.slskd-filename {
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.slskd-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--text-secondary);
}

.slskd-ext {
  color: #6495ED;
  font-weight: 600;
}

.slskd-user {
  color: var(--text-muted);
}

.slskd-check {
  color: #6495ED;
  font-size: 18px;
  font-weight: bold;
  margin-left: 12px;
}
</style>
