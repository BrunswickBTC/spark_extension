window.app.mixin({
  data() { return { selectedWalletId: null, loading: false, sending: false, sendingToken: false, balance: null, identity: null, adminStatus: null, statusError: null, transferRows: [], send: {amount_sats: null, address: '', wallet_id: null}, onchain: {address: null, deposit_id: null, loading: false}, token: {identifier: '', amount: null, address: ''}, transferColumns: [{name: 'status', label: 'Status', field: row => row.status || row.state || 'unknown'}, {name: 'amount', label: 'Amount', field: row => row.totalValue ?? row.amountSats ?? row.amount ?? ''}, {name: 'created', label: 'Created', field: row => row.userRequest?.createdAt || row.createdAt || ''}] } },
  computed: { isAdmin() { return !!this.g.user?.admin }, walletOptions() { return (this.g.user?.wallets || []).map(w => ({label: w.name, value: w.id})) }, canSend() { return !!this.send.wallet_id && Number(this.send.amount_sats) > 0 && !!this.send.address }, canSendToken() { return this.isAdmin && !!this.token.identifier && Number(this.token.amount) > 0 && !!this.token.address } },
  methods: {
    pretty(v) { return JSON.stringify(v, null, 2) }, copy(v) { if (v) LNbits.utils.copyText(v, 'Copied Spark address') },
    async request(method, path, body) { return (await LNbits.api.request(method, path, null, body)).data },
    async loadStatus() { this.loading = true; this.statusError = null; try { [this.balance, this.identity] = await Promise.all([this.request('POST', '/sparkl2/api/v1/balance', {}), this.request('GET', '/sparkl2/api/v1/identity')]); if (this.isAdmin) this.adminStatus = await this.request('GET', '/sparkl2/api/v1/admin/status') } catch (e) { this.statusError = e.response?.data?.detail || `Spark status unavailable (HTTP ${e.response?.status || 'error'})`; LNbits.utils.notifyApiError(e) } finally { this.loading = false } },
    async loadTransfers() { try { const d = await this.request('POST', '/sparkl2/api/v1/transfers', {limit: 100, offset: 0}); this.transferRows = Array.isArray(d) ? d : d?.transfers || d?.data || d?.items || [] } catch (e) { LNbits.utils.notifyApiError(e) } },
    async issueOnchainAddress() { if (!this.selectedWalletId) return; this.onchain.loading = true; try { const d = await this.request('POST', '/sparkl2/api/v1/receive/onchain', {wallet_id: this.selectedWalletId}); this.onchain = {...d, loading: false} } catch (e) { this.onchain.loading = false; LNbits.utils.notifyApiError(e) } },
    async sendSats() { if (this.send.address === this.identity?.spark_address) return Quasar.Notify.create({type: 'warning', message: "You can't send funds to yourself."}); if (!this.canSend || !window.confirm(`Send ${this.send.amount_sats} sats to this Spark address?`)) return; this.sending = true; try { await this.request('POST', '/sparkl2/api/v1/transfer', {wallet_id: this.send.wallet_id, amount_sats: Number(this.send.amount_sats), receiver_spark_address: this.send.address}); Quasar.Notify.create({type: 'positive', message: 'Spark sats transfer submitted'}); await this.loadStatus(); await this.loadTransfers() } catch (e) { LNbits.utils.notifyApiError(e) } finally { this.sending = false } },
    async sendTokens() { if (this.token.address === this.identity?.spark_address) return Quasar.Notify.create({type: 'warning', message: "You can't send tokens to yourself."}); if (!this.canSendToken || !window.confirm(`Send ${this.token.amount} tokens to this Spark address?`)) return; this.sendingToken = true; try { await this.request('POST', '/sparkl2/api/v1/tokens/transfer', {token_identifier: this.token.identifier, token_amount: String(this.token.amount), receiver_spark_address: this.token.address}); Quasar.Notify.create({type: 'positive', message: 'Spark token transfer submitted'}) } catch (e) { LNbits.utils.notifyApiError(e) } finally { this.sendingToken = false } }
  }, mounted() {
    if (!window.location.pathname.startsWith('/sparkl2')) return
    if (window.__sparkl2PageInitialized) return
    window.__sparkl2PageInitialized = true
    this.selectedWalletId = this.g.user?.wallets?.[0]?.id || null
    this.send.wallet_id = this.selectedWalletId
    this.loadStatus()
    this.loadTransfers()
  }
})
