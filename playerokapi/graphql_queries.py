"""
GraphQL-запросы к `https://playerok.com/graphql`.

Playerok использует Apollo Persisted Queries: большинство `query`-запросов на сайте отправляются
не полным текстом, а через GET с коротким `sha256Hash` (см. `PERSISTED_QUERIES`) — сервер уже знает
текст запроса по этому хэшу. Мутации и WS-подписки отправляются полным текстом (см. `QUERIES`).

`QUERY_TEXTS` хранит полные тексты persisted-запросов для APQ-фолбэка: если сервер ответил
`PERSISTED_QUERY_NOT_FOUND`, библиотека повторяет запрос POST'ом с полным текстом.

Тексты и хэши актуализированы по бандлу playerok.com (см. `graphql_collected.json` /
`tools/graphql/`, аудит 24.07.2026).
"""

PERSISTED_QUERIES: dict[str, str] = {
    'viewerBalance': 'a11039bbf514e8b9cb9901efbd81553574fab3bdcb75713afec40fb8de676d10',
    'user': '48cadfa521497f9445eaa9abda29a4251149636d9393f536165889a61e332384',
    'userChats': 'c1ddbcd7c8b87160ac25e0734f9dc32fc945287b056f4b14abf1473bfb1ad11a',
    'deals': '591b0e6d036c2120c8f95b97dbfdf5635df3747cd901f4895e009935229417ef',
    'deal': 'e572582c52871c15c3278d46c649c7ec70dd4711d80661a4aa3cc67b48823e3e',
    'testimonials': '773d40b7efec82a4b86021ba8bcaa462f68eb236e255926f2168c5cd4685e881',
    'games': '5de9b3240c148579c82e2310a30b4aad5462884fd1abf93dd3c43d1f5ef14d85',
    'GamePage': '4775f8630a3e234c50537e68649043ac32a40b0370b0f1fb2dc314500ef6202d',
    'GamePageCategory': '7759f743651176ddad6afefb5f2e889ec9984cae08a015281879cd61e94bdb60',
    'gameCategoryObtainingTypes': '15b0991414821528251930b4c8161c299eb39882fd635dd5adb1a81fb0570aea',
    'gameCategoryDataFields': '6fdadfb9b05880ce2d307a1412bc4f2e383683061c281e2b65a93f7266ea4a49',
    'chat': 'bb024dc0652fc7c1302a64a117d56d99fb0d726eb4b896ca803dca55f611d933',
    'chatMessages': '9b4e264ff1b20e0fd3929afe023dee8f50affc02b85f80cb4b3dc1516ecfbaa0',
    'items': 'bacca5d020eef37b4ff7a2253ad33ecd8b7e144b9ef854c20051f42ebcd04d82',
    'item': '014b7824712618664cdfd3223504f52f785a46b06561dd9e9c0e9d2e4d8262c6',
    'itemPriorityStatuses': 'b922220c6f979537e1b99de6af8f5c13727daeff66727f679f07f986ce1c025a',
    'messageTemplates': 'f3d4b4053f7c758d4cd84429bbf974a27b0afed6a473ab47fbe8d13ac6bf87a2',
    'viewerHasEnabledNotifications': 'e37e31e7b6ba73b9399bec6c1b8204b6efe98d6ab23f8a1015eba4ab0940c6c6',
    'chatAutoResponses': '7124fdad826e5668d0d91c186e320552fa7bf79dbbfe1f4ea3f8d0909ee48470',
}

# Полные тексты persisted-запросов (для APQ-фолбэка при устаревшем хэше).
QUERY_TEXTS: dict[str, str] = {
    'viewerBalance': """
query viewerBalance {
  viewer {
    id
    role
    balance {
      ...RegularUserBalance
      __typename
    }
    __typename
  }
}

fragment RegularUserBalance on UserBalance {
  id
  value
  frozen
  available
  withdrawable
  pendingIncome
  __typename
}
""",
    'user': """
query user($id: UUID, $username: String, $hasSupportAccess: Boolean!) {
  user(id: $id, username: $username) {
    ...RegularUserProfile
    ...UserVipStatusFragment @include(if: $hasSupportAccess)
    __typename
  }
}

fragment RegularUserProfile on UserProfile {
  ...RegularUser
  ...RegularUserFragment
  __typename
}

fragment RegularUser on User {
  id
  isBlocked
  isVerified
  isBlockedFor
  isFundsProtectionActive
  hasFrozenBalance
  username
  email
  role
  balance {
    ...RegularUserBalance
    __typename
  }
  profile {
    ...RegularUserFragment
    __typename
  }
  stats {
    ...RegularUserStats
    __typename
  }
  hasEnabledNotifications
  supportChatId
  systemChatId
  __typename
}

fragment RegularUserBalance on UserBalance {
  id
  value
  frozen
  available
  withdrawable
  pendingIncome
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment RegularUserStats on UserStats {
  id
  items {
    ...RegularUserItemsStats
    __typename
  }
  deals {
    ...RegularUserDealsStats
    __typename
  }
  fragmentDeposits {
    ...RegularUserFragmentDepositsStats
    __typename
  }
  steamDeposits {
    ...RegularUserSteamDepositsStats
    __typename
  }
  __typename
}

fragment RegularUserItemsStats on UserItemsStats {
  total
  finished
  __typename
}

fragment RegularUserDealsStats on UserDealsStats {
  incoming {
    total
    finished
    __typename
  }
  outgoing {
    total
    finished
    automatedTotal
    __typename
  }
  __typename
}

fragment RegularUserFragmentDepositsStats on UserFragmentDepositsStats {
  total
  finished
  __typename
}

fragment RegularUserSteamDepositsStats on UserSteamDepositsStats {
  total
  finished
  __typename
}

fragment UserVipStatusFragment on User {
  isVip
  vipLog {
    adminUsername
    createdAt
    event
    __typename
  }
  __typename
}
""",
    'userChats': """
query userChats($pagination: Pagination, $filter: ChatFilter) {
  chats(pagination: $pagination, filter: $filter) {
    edges {
      cursor
      node {
        id
        type
        status
        unreadMessagesCounter
        bookmarked
        lastMessage {
          ...ListLastChatMessageFields
          __typename
        }
        participants {
          ...ListChatParticipant
          __typename
        }
        __typename
      }
      __typename
    }
    pageInfo {
      startCursor
      endCursor
      hasPreviousPage
      hasNextPage
      __typename
    }
    totalCount
    __typename
  }
}

fragment ListLastChatMessageFields on ChatMessage {
  id
  text
  createdAt
  isRead
  isBulkMessaging
  event
  file {
    id
    url
    __typename
  }
  user {
    id
    username
    role
    __typename
  }
  eventByUser {
    id
    username
    __typename
  }
  eventToUser {
    id
    username
    __typename
  }
  deal {
    id
    direction
    status
    user {
      id
      username
      __typename
    }
    item {
      id
      sellerType
      user {
        id
        username
        __typename
      }
      __typename
    }
    __typename
  }
  images {
    id
    __typename
  }
  imageLinks
  __typename
}

fragment ListChatParticipant on UserFragment {
  id
  username
  avatarURL
  isOnline
  role
  isBlocked
  isVip
  __typename
}
""",
    'deals': """
query deals($pagination: Pagination, $filter: ItemDealFilter!, $sort: Sort, $showForbiddenImage: Boolean) {
  deals(pagination: $pagination, filter: $filter, sort: $sort) {
    edges {
      ...ItemDealEdgeFields
      __typename
    }
    pageInfo {
      startCursor
      endCursor
      hasPreviousPage
      hasNextPage
      __typename
    }
    totalCount
    __typename
  }
}

fragment ItemDealEdgeFields on ItemDealEdge {
  cursor
  node {
    ...ItemDealEdgeNodeFields
    __typename
  }
  __typename
}

fragment ItemDealEdgeNodeFields on ItemDeal {
  ...PartialItemDeal
  __typename
}

fragment PartialItemDeal on ItemDeal {
  id
  status
  direction
  statusDescription
  hasProblem
  user {
    ...RegularUserFragment
    __typename
  }
  item {
    id
    slug
    name
    price
    rawPrice
    attachments(showForbiddenImage: $showForbiddenImage) {
      ...PartialFile
      __typename
    }
    isAttachmentsForbidden
    user {
      ...RegularUserFragment
      __typename
    }
    __typename
  }
  testimonial {
    id
    rating
    __typename
  }
  isAutomated
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}
""",
    'deal': """
query deal($id: UUID!, $hasSupportAccess: Boolean!, $showForbiddenImage: Boolean) {
  deal(id: $id) {
    ...RegularItemDealWithUserVipStatus
    __typename
  }
}

fragment RegularItemDealWithUserVipStatus on ItemDeal {
  id
  status
  direction
  statusExpirationDate
  statusDescription
  obtaining
  hasProblem
  reportProblemEnabled
  completedBy {
    ...MinimalUserFragment
    __typename
  }
  props {
    ...ItemDealProps
    __typename
  }
  prevStatus
  completedAt
  createdAt
  logs {
    ...ItemLog
    __typename
  }
  transaction {
    ...ItemDealTransaction
    __typename
  }
  user {
    ...UserEdgeNode
    ...UserFragmentVipStatusFragment @include(if: $hasSupportAccess)
    __typename
  }
  chat {
    ...RegularChatId
    __typename
  }
  item {
    ...PartialDealItem
    user {
      ...UserEdgeNode
      ...UserFragmentVipStatusFragment @include(if: $hasSupportAccess)
      __typename
    }
    __typename
  }
  testimonial {
    ...RegularItemDealTestimonial
    __typename
  }
  obtainingFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  automationObtainingFields {
    ...ItemDealAutomationObtainingField
    __typename
  }
  commentFromBuyer
  obtainingTypeWarnings {
    ...ItemDealWarningFragment
    __typename
  }
  gameCategoryWarnings {
    ...ItemDealWarningFragment
    __typename
  }
  isAutomated
  __typename
}

fragment MinimalUserFragment on UserFragment {
  id
  username
  role
  __typename
}

fragment ItemDealProps on ItemDealProps {
  autoConfirmPeriod
  __typename
}

fragment ItemLog on ItemLog {
  id
  event
  createdAt
  user {
    ...UserEdgeNode
    __typename
  }
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment ItemDealTransaction on Transaction {
  id
  operation
  direction
  providerId
  status
  value
  createdAt
  paymentMethodId
  statusExpirationDate
  __typename
}

fragment UserFragmentVipStatusFragment on UserFragment {
  isVip
  __typename
}

fragment RegularChatId on Chat {
  id
  __typename
}

fragment PartialDealItem on Item {
  ...PartialDealMyItem
  ...PartialDealForeignItem
  __typename
}

fragment PartialDealMyItem on MyItem {
  id
  slug
  priority
  status
  name
  price
  priorityPrice
  rawPrice
  statusExpirationDate
  sellerType
  approvalDate
  createdAt
  priorityPosition
  viewsCounter
  feeMultiplier
  comment
  attachments(showForbiddenImage: $showForbiddenImage) {
    ...RegularFile
    __typename
  }
  isAttachmentsForbidden
  user {
    ...UserEdgeNode
    __typename
  }
  game {
    ...RegularGameProfile
    __typename
  }
  category {
    ...MinimalGameCategory
    __typename
  }
  dataFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  obtainingType {
    ...MinimalGameCategoryObtainingType
    __typename
  }
  __typename
}

fragment RegularFile on File {
  id
  url
  filename
  mime
  __typename
}

fragment RegularGameProfile on GameProfile {
  id
  name
  type
  slug
  logo {
    ...PartialFile
    __typename
  }
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment MinimalGameCategory on GameCategory {
  id
  slug
  name
  __typename
}

fragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {
  id
  label
  type
  inputType
  copyable
  hidden
  required
  value
  __typename
}

fragment MinimalGameCategoryObtainingType on GameCategoryObtainingType {
  id
  name
  description
  gameCategoryId
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  sequence
  feeMultiplier
  props {
    minTestimonialsForSeller
    __typename
  }
  __typename
}

fragment PartialDealForeignItem on ForeignItem {
  id
  slug
  priority
  status
  name
  price
  rawPrice
  sellerType
  approvalDate
  priorityPosition
  createdAt
  viewsCounter
  feeMultiplier
  comment
  attachments(showForbiddenImage: $showForbiddenImage) {
    ...RegularFile
    __typename
  }
  isAttachmentsForbidden
  user {
    ...UserEdgeNode
    __typename
  }
  game {
    ...RegularGameProfile
    __typename
  }
  category {
    ...MinimalGameCategory
    __typename
  }
  dataFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  obtainingType {
    ...MinimalGameCategoryObtainingType
    __typename
  }
  __typename
}

fragment RegularItemDealTestimonial on Testimonial {
  id
  status
  text
  rating
  createdAt
  updatedAt
  creator {
    ...RegularUserFragment
    __typename
  }
  moderator {
    ...RegularUserFragment
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  __typename
}

fragment ItemDealAutomationObtainingField on AutomationObtainingFieldItemDeals {
  code
  value
  name
  __typename
}

fragment ItemDealWarningFragment on ItemDealWarning {
  id
  status
  title
  text
  __typename
}
""",
    'testimonials': """
query testimonials($pagination: Pagination, $sort: Sort, $filter: TestimonialFilter!, $hasSupportAccess: Boolean!) {
  testimonials(pagination: $pagination, sort: $sort, filter: $filter) {
    edges {
      cursor
      node {
        ...MinifiedTestimonial
        creator {
          ...RegularUserFragment
          ...UserFragmentVipStatusFragment @include(if: $hasSupportAccess)
          __typename
        }
        __typename
      }
      __typename
    }
    pageInfo {
      startCursor
      endCursor
      hasPreviousPage
      hasNextPage
      __typename
    }
    totalCount
    __typename
  }
}

fragment MinifiedTestimonial on Testimonial {
  id
  status
  text
  rating
  createdAt
  updatedAt
  deal {
    ...DealProfileForTestimonials
    __typename
  }
  creator {
    ...RegularUserFragment
    __typename
  }
  moderator {
    ...RegularUserFragment
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  __typename
}

fragment DealProfileForTestimonials on ItemDealProfile {
  id
  direction
  status
  item {
    ...TestimonialItemProfile
    __typename
  }
  __typename
}

fragment TestimonialItemProfile on ItemProfile {
  id
  slug
  priority
  status
  name
  price
  rawPrice
  approvalDate
  createdAt
  sellerType
  attachment {
    ...PartialFile
    __typename
  }
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment UserFragmentVipStatusFragment on UserFragment {
  isVip
  __typename
}
""",
    'games': """
query games($pagination: Pagination, $filter: GameFilter, $sort: Sort) {
  games(pagination: $pagination, filter: $filter, sort: $sort) {
    ...GameList
    __typename
  }
}

fragment GameList on GameList {
  edges {
    ...GameEdgeFields
    __typename
  }
  pageInfo {
    startCursor
    endCursor
    hasPreviousPage
    hasNextPage
    __typename
  }
  totalCount
  __typename
}

fragment GameEdgeFields on GameEdge {
  cursor
  node {
    ...GameEdgeNode
    __typename
  }
  __typename
}

fragment GameEdgeNode on Game {
  id
  slug
  name
  type
  isNew
  logo {
    ...RegularFile
    __typename
  }
  categories {
    ...GameEdgeNodeGameCategory
    __typename
  }
  createdAt
  __typename
}

fragment RegularFile on File {
  id
  url
  filename
  mime
  __typename
}

fragment GameEdgeNodeGameCategory on GameCategory {
  id
  slug
  name
  __typename
}
""",
    'GamePage': """
query GamePage($id: UUID, $slug: String) {
  game(id: $id, slug: $slug) {
    ...GamePageFragment
    __typename
  }
}

fragment GamePageFragment on Game {
  id
  slug
  name
  type
  isNew
  logo {
    ...RegularFile
    __typename
  }
  banner {
    ...RegularFile
    __typename
  }
  categories {
    ...MinimalGameCategory
    __typename
  }
  createdAt
  __typename
}

fragment RegularFile on File {
  id
  url
  filename
  mime
  __typename
}

fragment MinimalGameCategory on GameCategory {
  id
  slug
  name
  __typename
}
""",
    'GamePageCategory': """
query GamePageCategory($id: UUID, $slug: String) {
  gameCategory(id: $id, slug: $slug) {
    ...GamePageCategoryFragment
    seo {
      ...GameCategorySeo
      __typename
    }
    __typename
  }
}

fragment GamePageCategoryFragment on GameCategory {
  id
  slug
  name
  options {
    ...RegularGameCategoryOption
    __typename
  }
  useCustomObtaining
  __typename
}

fragment RegularGameCategoryOption on GameCategoryOption {
  id
  group
  label
  type
  field
  value
  valueRangeLimit {
    min
    max
    __typename
  }
  multiple
  __typename
}

fragment GameCategorySeo on GameCategorySeo {
  id
  seoText
  metaTitle
  metaDescription
  metaKeywords
  metaRobots
  metaLang
  metaViewport
  __typename
}
""",
    'gameCategoryObtainingTypes': """
query gameCategoryObtainingTypes($pagination: Pagination, $filter: GameCategoryObtainingTypeFilter!) {
  gameCategoryObtainingTypes(pagination: $pagination, filter: $filter) {
    ...GameCategoryObtainingTypeList
    __typename
  }
}

fragment GameCategoryObtainingTypeList on GameCategoryObtainingTypeList {
  edges {
    ...GameCategoryObtainingTypeEdge
    __typename
  }
  pageInfo {
    startCursor
    endCursor
    hasPreviousPage
    hasNextPage
    __typename
  }
  totalCount
  __typename
}

fragment GameCategoryObtainingTypeEdge on GameCategoryObtainingTypeEdge {
  cursor
  node {
    ...GameCategoryObtainingType
    __typename
  }
  __typename
}

fragment GameCategoryObtainingType on GameCategoryObtainingType {
  id
  name
  description
  gameCategoryId
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  sequence
  feeMultiplier
  agreements {
    ...MinimalGameCategoryAgreement
    __typename
  }
  props {
    minTestimonialsForSeller
    __typename
  }
  __typename
}

fragment MinimalGameCategoryAgreement on GameCategoryAgreement {
  description
  iconType
  id
  sequence
  __typename
}
""",
    'gameCategoryDataFields': """
query gameCategoryDataFields($pagination: Pagination, $filter: GameCategoryDataFieldFilter!) {
  gameCategoryDataFields(pagination: $pagination, filter: $filter) {
    ...GameCategoryDataFieldList
    __typename
  }
}

fragment GameCategoryDataFieldList on GameCategoryDataFieldList {
  edges {
    ...GameCategoryDataFieldEdge
    __typename
  }
  pageInfo {
    startCursor
    endCursor
    hasPreviousPage
    hasNextPage
    __typename
  }
  totalCount
  __typename
}

fragment GameCategoryDataFieldEdge on GameCategoryDataFieldEdge {
  cursor
  node {
    ...MinimalGameCategoryDataField
    __typename
  }
  __typename
}

fragment MinimalGameCategoryDataField on GameCategoryDataField {
  id
  label
  type
  inputType
  copyable
  hidden
  required
  sequence
  validationRules {
    ...GameCategoryDataFieldValidationRules
    __typename
  }
  __typename
}

fragment GameCategoryDataFieldValidationRules on GameCategoryDataFieldValidationRules {
  id
  minLength
  maxLength
  regExp
  __typename
}
""",
    'chat': """
query chat($id: UUID!, $hasSupportAccess: Boolean!) {
  chat(id: $id) {
    ...RegularChatWithUserVipStatus
    __typename
  }
}

fragment RegularChatWithUserVipStatus on Chat {
  id
  type
  unreadMessagesCounter
  bookmarked
  isTextingAllowed
  owner {
    ...ChatParticipant
    __typename
  }
  agent {
    ...ChatParticipant
    __typename
  }
  participants {
    ...ChatParticipant
    ...UserFragmentVipStatusFragment @include(if: $hasSupportAccess)
    __typename
  }
  deals {
    ...ChatActiveItemDeal
    item {
      ...ChatDealMyItemEdgeNode
      ...ChatDealForeignItemEdgeNode
      user {
        ...UserItemEdgeNode
        ...UserFragmentVipStatusFragment @include(if: $hasSupportAccess)
        __typename
      }
      __typename
    }
    user {
      ...RegularUserFragment
      ...UserFragmentVipStatusFragment @include(if: $hasSupportAccess)
      __typename
    }
    __typename
  }
  status
  startedAt
  finishedAt
  __typename
}

fragment ChatParticipant on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment UserFragmentVipStatusFragment on UserFragment {
  isVip
  __typename
}

fragment ChatActiveItemDeal on ItemDealProfile {
  id
  direction
  status
  hasProblem
  testimonial {
    id
    rating
    __typename
  }
  item {
    ...ChatDealItemEdgeNode
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  __typename
}

fragment ChatDealItemEdgeNode on ItemProfile {
  ...ChatDealMyItemEdgeNode
  ...ChatDealForeignItemEdgeNode
  __typename
}

fragment ChatDealMyItemEdgeNode on MyItemProfile {
  id
  slug
  priority
  status
  name
  price
  rawPrice
  statusExpirationDate
  sellerType
  attachment {
    ...PartialFile
    __typename
  }
  user {
    ...UserItemEdgeNode
    __typename
  }
  approvalDate
  createdAt
  priorityPosition
  feeMultiplier
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment UserItemEdgeNode on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment ChatDealForeignItemEdgeNode on ForeignItemProfile {
  id
  slug
  priority
  status
  name
  price
  rawPrice
  sellerType
  attachment {
    ...PartialFile
    __typename
  }
  user {
    ...UserItemEdgeNode
    __typename
  }
  approvalDate
  priorityPosition
  createdAt
  feeMultiplier
  __typename
}
""",
    'chatMessages': """
query chatMessages($hasSupportAccess: Boolean!, $pagination: Pagination, $filter: ChatMessageFilter, $showForbiddenImage: Boolean) {
  chatMessages(pagination: $pagination, filter: $filter) {
    edges {
      ...ChatMessageEdgeFields
      __typename
    }
    pageInfo {
      startCursor
      endCursor
      hasPreviousPage
      hasNextPage
      __typename
    }
    totalCount
    __typename
  }
}

fragment ChatMessageEdgeFields on ChatMessageEdge {
  cursor
  node {
    ...RegularChatMessageWithUserVipStatus
    __typename
  }
  __typename
}

fragment RegularChatMessageWithUserVipStatus on ChatMessage {
  id
  text
  createdAt
  deletedAt
  isRead
  isSuspicious
  isBulkMessaging
  game {
    ...RegularGameProfile
    __typename
  }
  file {
    ...PartialFile
    __typename
  }
  user {
    ...ChatMessageUserFields
    ...UserFragmentVipStatusFragment @include(if: $hasSupportAccess)
    __typename
  }
  deal {
    ...ChatMessageItemDeal
    testimonial {
      ...ChatMessageDealTestimonial
      creator {
        ...RegularUserFragment
        ...UserFragmentVipStatusFragment @include(if: $hasSupportAccess)
        __typename
      }
      __typename
    }
    user {
      ...ChatParticipant
      ...UserFragmentVipStatusFragment @include(if: $hasSupportAccess)
      __typename
    }
    item {
      id
      name
      price
      slug
      rawPrice
      sellerType
      user {
        ...ChatParticipant
        ...UserFragmentVipStatusFragment @include(if: $hasSupportAccess)
        __typename
      }
      category {
        id
        __typename
      }
      attachments(showForbiddenImage: $showForbiddenImage) {
        ...PartialFile
        __typename
      }
      comment
      dataFields {
        ...GameCategoryDataFieldWithValue
        __typename
      }
      obtainingType {
        ...GameCategoryObtainingType
        __typename
      }
      __typename
    }
    __typename
  }
  item {
    ...ItemEdgeNode
    __typename
  }
  transaction {
    ...RegularTransaction
    __typename
  }
  moderator {
    ...UserEdgeNode
    __typename
  }
  eventByUser {
    ...ChatMessageUserFields
    __typename
  }
  eventToUser {
    ...ChatMessageUserFields
    __typename
  }
  isAutoResponse
  event
  buttons {
    ...ChatMessageButton
    __typename
  }
  images {
    ...PartialFile
    __typename
  }
  imageLinks
  uncensorInfo {
    count
    lastEvent {
      username
      createdAt
      __typename
    }
    __typename
  }
  plTokenAmount
  __typename
}

fragment RegularGameProfile on GameProfile {
  id
  name
  type
  slug
  logo {
    ...PartialFile
    __typename
  }
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment ChatMessageUserFields on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment UserFragmentVipStatusFragment on UserFragment {
  isVip
  __typename
}

fragment ChatMessageItemDeal on ItemDeal {
  id
  direction
  status
  statusDescription
  hasProblem
  user {
    ...ChatParticipant
    __typename
  }
  testimonial {
    ...ChatMessageDealTestimonial
    __typename
  }
  item {
    id
    name
    price
    slug
    rawPrice
    sellerType
    user {
      ...ChatParticipant
      __typename
    }
    category {
      id
      __typename
    }
    attachments(showForbiddenImage: $showForbiddenImage) {
      ...PartialFile
      __typename
    }
    isAttachmentsForbidden
    comment
    dataFields {
      ...GameCategoryDataFieldWithValue
      __typename
    }
    obtainingType {
      ...GameCategoryObtainingType
      __typename
    }
    __typename
  }
  obtainingFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  automationObtainingFields {
    ...ItemDealAutomationObtainingField
    __typename
  }
  chat {
    id
    type
    __typename
  }
  transaction {
    id
    statusExpirationDate
    __typename
  }
  statusExpirationDate
  commentFromBuyer
  gameCategoryWarnings {
    ...ItemDealWarningFragment
    __typename
  }
  obtainingTypeWarnings {
    ...ItemDealWarningFragment
    __typename
  }
  __typename
}

fragment ChatParticipant on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment ChatMessageDealTestimonial on Testimonial {
  id
  status
  text
  rating
  createdAt
  updatedAt
  creator {
    ...RegularUserFragment
    __typename
  }
  moderator {
    ...RegularUserFragment
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  __typename
}

fragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {
  id
  label
  type
  inputType
  copyable
  hidden
  required
  value
  __typename
}

fragment GameCategoryObtainingType on GameCategoryObtainingType {
  id
  name
  description
  gameCategoryId
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  sequence
  feeMultiplier
  agreements {
    ...MinimalGameCategoryAgreement
    __typename
  }
  props {
    minTestimonialsForSeller
    __typename
  }
  __typename
}

fragment MinimalGameCategoryAgreement on GameCategoryAgreement {
  description
  iconType
  id
  sequence
  __typename
}

fragment ItemDealAutomationObtainingField on AutomationObtainingFieldItemDeals {
  code
  value
  name
  __typename
}

fragment ItemDealWarningFragment on ItemDealWarning {
  id
  status
  title
  text
  __typename
}

fragment ItemEdgeNode on ItemProfile {
  ...MyItemEdgeNode
  ...ForeignItemEdgeNode
  __typename
}

fragment MyItemEdgeNode on MyItemProfile {
  id
  slug
  priority
  status
  name
  price
  rawPrice
  statusExpirationDate
  sellerType
  attachment(showForbiddenImage: $showForbiddenImage) {
    ...PartialFile
    __typename
  }
  isAttachmentsForbidden
  user {
    ...UserItemEdgeNode
    __typename
  }
  game {
    name
    __typename
  }
  category {
    name
    __typename
  }
  approvalDate
  createdAt
  priorityPosition
  viewsCounter
  dealsCounter
  feeMultiplier
  isAutomated
  __typename
}

fragment UserItemEdgeNode on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment ForeignItemEdgeNode on ForeignItemProfile {
  id
  slug
  priority
  status
  name
  price
  rawPrice
  sellerType
  attachment(showForbiddenImage: $showForbiddenImage) {
    ...PartialFile
    __typename
  }
  isAttachmentsForbidden
  user {
    ...UserItemEdgeNode
    __typename
  }
  game {
    name
    __typename
  }
  category {
    name
    __typename
  }
  approvalDate
  priorityPosition
  createdAt
  viewsCounter
  dealsCounter
  feeMultiplier
  isAutomated
  __typename
}

fragment RegularTransaction on Transaction {
  id
  operation
  direction
  providerId
  provider {
    ...RegularTransactionProvider
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  creator {
    ...RegularUserFragment
    __typename
  }
  status
  statusDescription
  statusExpirationDate
  value
  fee
  createdAt
  props {
    ...RegularTransactionProps
    __typename
  }
  verifiedAt
  verifiedBy {
    ...UserEdgeNode
    __typename
  }
  completedBy {
    ...UserEdgeNode
    __typename
  }
  paymentMethodId
  completedAt
  isSuspicious
  spbBankName
  autoClaimedAt
  __typename
}

fragment RegularTransactionProvider on TransactionProvider {
  id
  name
  fee
  minFeeAmount
  description
  account {
    ...RegularTransactionProviderAccount
    __typename
  }
  props {
    ...TransactionProviderPropsFragment
    __typename
  }
  limits {
    ...ProviderLimits
    __typename
  }
  paymentMethods {
    ...TransactionPaymentMethod
    __typename
  }
  __typename
}

fragment RegularTransactionProviderAccount on TransactionProviderAccount {
  id
  value
  userId
  providerId
  paymentMethodId
  __typename
}

fragment TransactionProviderPropsFragment on TransactionProviderPropsFragment {
  requiredUserData {
    ...TransactionProviderRequiredUserData
    __typename
  }
  tooltip
  __typename
}

fragment TransactionProviderRequiredUserData on TransactionProviderRequiredUserData {
  email
  phoneNumber
  eripAccountNumber
  __typename
}

fragment ProviderLimits on ProviderLimits {
  incoming {
    ...ProviderLimitRange
    __typename
  }
  outgoing {
    ...ProviderLimitRange
    __typename
  }
  __typename
}

fragment ProviderLimitRange on ProviderLimitRange {
  min
  max
  __typename
}

fragment TransactionPaymentMethod on TransactionPaymentMethod {
  id
  name
  fee
  providerId
  account {
    ...RegularTransactionProviderAccount
    __typename
  }
  props {
    ...TransactionProviderPropsFragment
    __typename
  }
  limits {
    ...ProviderLimits
    __typename
  }
  __typename
}

fragment RegularTransactionProps on TransactionPropsFragment {
  creatorId
  dealId
  paidFromPendingIncome
  paymentURL
  successURL
  fee
  paymentAccount {
    id
    value
    __typename
  }
  paymentGateway
  alreadySpent
  exchangeRate
  amountAfterConversionRub
  amountAfterConversionUsdt
  fragmentUsername
  userData {
    account
    email
    ipAddress
    phoneNumber
    __typename
  }
  __typename
}

fragment ChatMessageButton on ChatMessageButton {
  type
  url
  text
  __typename
}
""",
    'items': """
query items($filter: ItemFilter, $pagination: Pagination, $sort: Sort, $showForbiddenImage: Boolean) {
items(filter: $filter, pagination: $pagination, sort: $sort) {
edges {
...ItemEdgeFields
__typename
}
pageInfo {
startCursor
endCursor
hasPreviousPage
hasNextPage
__typename
}
totalCount
__typename
}
}
fragment ItemEdgeFields on ItemProfileEdge {
cursor
node {
...ItemEdgeNode
__typename
}
__typename
}
fragment ItemEdgeNode on ItemProfile {
...MyItemEdgeNode
...ForeignItemEdgeNode
__typename
}
fragment MyItemEdgeNode on MyItemProfile {
id
slug
priority
status
name
price
rawPrice
statusExpirationDate
sellerType
attachment(showForbiddenImage: $showForbiddenImage) {
...PartialFile
__typename
}
isAttachmentsForbidden
user {
...UserItemEdgeNode
__typename
}
game {
name
__typename
}
category {
name
__typename
}
approvalDate
createdAt
priorityPosition
viewsCounter
dealsCounter
feeMultiplier
isAutomated
__typename
}
fragment PartialFile on File {
id
url
__typename
}
fragment UserItemEdgeNode on UserFragment {
...UserEdgeNode
__typename
}
fragment UserEdgeNode on UserFragment {
...RegularUserFragment
__typename
}
fragment RegularUserFragment on UserFragment {
id
username
role
avatarURL
isOnline
isBlocked
rating
testimonialCounter
createdAt
supportChatId
systemChatId
__typename
}
fragment ForeignItemEdgeNode on ForeignItemProfile {
id
slug
priority
status
name
price
rawPrice
sellerType
attachment(showForbiddenImage: $showForbiddenImage) {
...PartialFile
__typename
}
isAttachmentsForbidden
user {
...UserItemEdgeNode
__typename
}
game {
name
__typename
}
category {
name
__typename
}
approvalDate
priorityPosition
createdAt
viewsCounter
dealsCounter
feeMultiplier
isAutomated
__typename
}
""",
'item': """
query item($slug: String, $id: UUID, $hasSupportAccess: Boolean!, $showForbiddenImage: Boolean) {
  item(slug: $slug, id: $id) {
    ...RegularItemWithUserVipStatus
    __typename
  }
}

fragment RegularItemWithUserVipStatus on Item {
  ...RegularMyItem
  ...RegularForeignItem
  user {
    ...ItemUser
    ...UserFragmentVipStatusFragment @include(if: $hasSupportAccess)
    __typename
  }
  __typename
}

fragment RegularMyItem on MyItem {
  ...ItemFields
  prevPrice
  priority
  sequence
  priorityPrice
  statusExpirationDate
  comment
  viewsCounter
  dealsCounter
  statusDescription
  editable
  statusPayment {
    ...StatusPaymentTransaction
    __typename
  }
  moderator {
    id
    username
    __typename
  }
  approvalDate
  deletedAt
  createdAt
  updatedAt
  mayBePublished
  prevFeeMultiplier
  sellerNotifiedAboutFeeChange
  postModerationCheckedAt
  __typename
}

fragment ItemFields on Item {
  id
  slug
  name
  description
  rawPrice
  price
  attributes
  status
  priorityPosition
  sellerType
  feeMultiplier
  user {
    ...ItemUser
    __typename
  }
  buyer {
    ...ItemUser
    __typename
  }
  attachments(showForbiddenImage: $showForbiddenImage) {
    ...PartialFile
    __typename
  }
  isAutomated
  isAttachmentsForbidden
  category {
    ...RegularGameCategory
    __typename
  }
  game {
    ...RegularGameProfile
    __typename
  }
  comment
  dataFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  obtainingType {
    ...GameCategoryObtainingType
    __typename
  }
  __typename
}

fragment ItemUser on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment RegularGameCategory on GameCategory {
  id
  slug
  name
  categoryId
  gameId
  obtaining
  options {
    ...RegularGameCategoryOption
    __typename
  }
  props {
    ...GameCategoryProps
    __typename
  }
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  useCustomObtaining
  autoConfirmPeriod
  autoModerationMode
  agreements {
    ...RegularGameCategoryAgreement
    __typename
  }
  feeMultiplier
  __typename
}

fragment RegularGameCategoryOption on GameCategoryOption {
  id
  group
  label
  type
  field
  value
  valueRangeLimit {
    min
    max
    __typename
  }
  multiple
  __typename
}

fragment GameCategoryProps on GameCategoryPropsObjectType {
  minTestimonials
  minTestimonialsForSeller
  __typename
}

fragment RegularGameCategoryAgreement on GameCategoryAgreement {
  description
  gameCategoryId
  gameCategoryObtainingTypeId
  iconType
  id
  sequence
  __typename
}

fragment RegularGameProfile on GameProfile {
  id
  name
  type
  slug
  logo {
    ...PartialFile
    __typename
  }
  __typename
}

fragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {
  id
  label
  type
  inputType
  copyable
  hidden
  required
  value
  __typename
}

fragment GameCategoryObtainingType on GameCategoryObtainingType {
  id
  name
  description
  gameCategoryId
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  sequence
  feeMultiplier
  agreements {
    ...MinimalGameCategoryAgreement
    __typename
  }
  props {
    minTestimonialsForSeller
    __typename
  }
  __typename
}

fragment MinimalGameCategoryAgreement on GameCategoryAgreement {
  description
  iconType
  id
  sequence
  __typename
}

fragment StatusPaymentTransaction on Transaction {
  id
  operation
  direction
  providerId
  status
  statusDescription
  statusExpirationDate
  value
  props {
    paymentURL
    __typename
  }
  __typename
}

fragment RegularForeignItem on ForeignItem {
  ...ItemFields
  postModerationCheckedAt
  __typename
}

fragment UserFragmentVipStatusFragment on UserFragment {
  isVip
  __typename
}
""",
    'itemPriorityStatuses': """
query itemPriorityStatuses($price: NonNegativeFloat!, $itemId: UUID) {
  itemPriorityStatuses(price: $price, itemId: $itemId) {
    ...MinimalItemPriorityStatus
    __typename
  }
}

fragment MinimalItemPriorityStatus on ItemPriorityStatus {
  id
  price
  name
  type
  period
  priceRange {
    min
    max
    __typename
  }
  __typename
}
""",
    'messageTemplates': """
query messageTemplates($pagination: Pagination, $sort: Sort, $filter: MessageTemplateFilter!) {
  messageTemplates(pagination: $pagination, sort: $sort, filter: $filter) {
    edges {
      ...MessageTemplateEdgeFields
      __typename
    }
    pageInfo {
      startCursor
      endCursor
      hasPreviousPage
      hasNextPage
      __typename
    }
    totalCount
    __typename
  }
}

fragment MessageTemplateEdgeFields on MessageTemplateEdge {
  cursor
  node {
    ...MessageTemplate
    __typename
  }
  __typename
}

fragment MessageTemplate on MessageTemplate {
  id
  type
  title
  text
  sequence
  createdAt
  group {
    ...MessageTemplateGroup
    __typename
  }
  __typename
}

fragment MessageTemplateGroup on MessageTemplateGroup {
  id
  type
  title
  createdAt
  sequence
  templatesCounter
  __typename
}
""",
    'viewerHasEnabledNotifications': """
query viewerHasEnabledNotifications {
  viewer {
    ...ViewerHasEnabledNotifications
    __typename
  }
}

fragment ViewerHasEnabledNotifications on User {
  id
  hasEnabledNotifications
  shouldShowEnableNotifications
  __typename
}
""",
    'chatAutoResponses': """
query chatAutoResponses($pagination: Pagination, $filter: ChatAutoResponseFilter!) {
  chatAutoResponses(pagination: $pagination, filter: $filter) {
    ...ChatAutoResponseList
    __typename
  }
}

fragment ChatAutoResponseList on ChatAutoResponseList {
  edges {
    ...ChatAutoResponseEdgeFields
    __typename
  }
  pageInfo {
    startCursor
    endCursor
    hasPreviousPage
    hasNextPage
    __typename
  }
  totalCount
  __typename
}

fragment ChatAutoResponseEdgeFields on ChatAutoResponseEdge {
  cursor
  node {
    ...ChatAutoResponse
    __typename
  }
  __typename
}

fragment ChatAutoResponse on ChatAutoResponse {
  id
  parentQuestionId
  question
  answer
  createdAt
  sequence
  trigger
  parentQuestion {
    ...ChatAutoResponseParentQuestion
    __typename
  }
  __typename
}

fragment ChatAutoResponseParentQuestion on ChatAutoResponse {
  id
  question
  __typename
}
""",
}

QUERIES: dict[str, str] = {
    'viewer': """
query viewer {
  viewer {
    ...Viewer
    __typename
  }
}

fragment Viewer on User {
  id
  username
  email
  role
  hasFrozenBalance
  supportChatId
  systemChatId
  unreadChatsCounter
  isBlocked
  isBlockedFor
  isFundsProtectionActive
  createdAt
  lastItemCreatedAt
  hasConfirmedPhoneNumber
  canPublishItems
  chosenVerifiedCard {
    ...MinimalUserBankCard
    __typename
  }
  balance {
    value
    __typename
  }
  profile {
    id
    avatarURL
    testimonialCounter
    __typename
  }
  __typename
}

fragment MinimalUserBankCard on UserBankCard {
  id
  cardFirstSix
  cardLastFour
  cardType
  isChosen
  __typename
}
""",
    'markChatAsRead': """
mutation markChatAsRead($input: MarkChatAsReadInput!) {
  markChatAsRead(input: $input) {
    ...RegularChat
    __typename
  }
}

fragment RegularChat on Chat {
  id
  type
  unreadMessagesCounter
  bookmarked
  isTextingAllowed
  owner {
    ...ChatParticipant
    __typename
  }
  agent {
    ...ChatParticipant
    __typename
  }
  participants {
    ...ChatParticipant
    __typename
  }
  deals {
    ...ChatActiveItemDeal
    __typename
  }
  status
  startedAt
  finishedAt
  __typename
}

fragment ChatParticipant on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment ChatActiveItemDeal on ItemDealProfile {
  id
  direction
  status
  hasProblem
  testimonial {
    id
    rating
    __typename
  }
  item {
    ...ChatDealItemEdgeNode
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  __typename
}

fragment ChatDealItemEdgeNode on ItemProfile {
  ...ChatDealMyItemEdgeNode
  ...ChatDealForeignItemEdgeNode
  __typename
}

fragment ChatDealMyItemEdgeNode on MyItemProfile {
  id
  slug
  priority
  status
  name
  price
  rawPrice
  statusExpirationDate
  sellerType
  attachment {
    ...PartialFile
    __typename
  }
  user {
    ...UserItemEdgeNode
    __typename
  }
  approvalDate
  createdAt
  priorityPosition
  feeMultiplier
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment UserItemEdgeNode on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment ChatDealForeignItemEdgeNode on ForeignItemProfile {
  id
  slug
  priority
  status
  name
  price
  rawPrice
  sellerType
  attachment {
    ...PartialFile
    __typename
  }
  user {
    ...UserItemEdgeNode
    __typename
  }
  approvalDate
  priorityPosition
  createdAt
  feeMultiplier
  __typename
}
""",
    'createChatMessage': """
mutation createChatMessage($input: CreateChatMessageInput!, $file: Upload, $showForbiddenImage: Boolean) {
  createChatMessage(input: $input, file: $file) {
    ...RegularChatMessage
    __typename
  }
}

fragment RegularChatMessage on ChatMessage {
  id
  text
  createdAt
  deletedAt
  isRead
  isSuspicious
  isBulkMessaging
  game {
    ...RegularGameProfile
    __typename
  }
  file {
    ...PartialFile
    __typename
  }
  user {
    ...ChatMessageUserFields
    __typename
  }
  deal {
    ...ChatMessageItemDeal
    __typename
  }
  item {
    ...ItemEdgeNode
    __typename
  }
  transaction {
    ...RegularTransaction
    __typename
  }
  moderator {
    ...UserEdgeNode
    __typename
  }
  eventByUser {
    ...ChatMessageUserFields
    __typename
  }
  eventToUser {
    ...ChatMessageUserFields
    __typename
  }
  isAutoResponse
  event
  buttons {
    ...ChatMessageButton
    __typename
  }
  images {
    ...RegularFile
    __typename
  }
  imageLinks
  uncensorInfo {
    count
    lastEvent {
      username
      createdAt
      __typename
    }
    __typename
  }
  plTokenAmount
  __typename
}

fragment RegularGameProfile on GameProfile {
  id
  name
  type
  slug
  logo {
    ...PartialFile
    __typename
  }
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment ChatMessageUserFields on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment ChatMessageItemDeal on ItemDeal {
  id
  direction
  status
  statusDescription
  hasProblem
  user {
    ...ChatParticipant
    __typename
  }
  testimonial {
    ...ChatMessageDealTestimonial
    __typename
  }
  item {
    id
    name
    price
    slug
    rawPrice
    sellerType
    user {
      ...ChatParticipant
      __typename
    }
    category {
      id
      __typename
    }
    attachments(showForbiddenImage: $showForbiddenImage) {
      ...PartialFile
      __typename
    }
    isAttachmentsForbidden
    comment
    dataFields {
      ...GameCategoryDataFieldWithValue
      __typename
    }
    obtainingType {
      ...GameCategoryObtainingType
      __typename
    }
    __typename
  }
  obtainingFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  automationObtainingFields {
    ...ItemDealAutomationObtainingField
    __typename
  }
  chat {
    id
    type
    __typename
  }
  transaction {
    id
    statusExpirationDate
    __typename
  }
  statusExpirationDate
  commentFromBuyer
  gameCategoryWarnings {
    ...ItemDealWarningFragment
    __typename
  }
  obtainingTypeWarnings {
    ...ItemDealWarningFragment
    __typename
  }
  __typename
}

fragment ChatParticipant on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment ChatMessageDealTestimonial on Testimonial {
  id
  status
  text
  rating
  createdAt
  updatedAt
  creator {
    ...RegularUserFragment
    __typename
  }
  moderator {
    ...RegularUserFragment
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  __typename
}

fragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {
  id
  label
  type
  inputType
  copyable
  hidden
  required
  value
  __typename
}

fragment GameCategoryObtainingType on GameCategoryObtainingType {
  id
  name
  description
  gameCategoryId
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  sequence
  feeMultiplier
  agreements {
    ...MinimalGameCategoryAgreement
    __typename
  }
  props {
    minTestimonialsForSeller
    __typename
  }
  __typename
}

fragment MinimalGameCategoryAgreement on GameCategoryAgreement {
  description
  iconType
  id
  sequence
  __typename
}

fragment ItemDealAutomationObtainingField on AutomationObtainingFieldItemDeals {
  code
  value
  name
  __typename
}

fragment ItemDealWarningFragment on ItemDealWarning {
  id
  status
  title
  text
  __typename
}

fragment ItemEdgeNode on ItemProfile {
  ...MyItemEdgeNode
  ...ForeignItemEdgeNode
  __typename
}

fragment MyItemEdgeNode on MyItemProfile {
  id
  slug
  priority
  status
  name
  price
  rawPrice
  statusExpirationDate
  sellerType
  attachment(showForbiddenImage: $showForbiddenImage) {
    ...PartialFile
    __typename
  }
  isAttachmentsForbidden
  user {
    ...UserItemEdgeNode
    __typename
  }
  game {
    name
    __typename
  }
  category {
    name
    __typename
  }
  approvalDate
  createdAt
  priorityPosition
  viewsCounter
  dealsCounter
  feeMultiplier
  isAutomated
  __typename
}

fragment UserItemEdgeNode on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment ForeignItemEdgeNode on ForeignItemProfile {
  id
  slug
  priority
  status
  name
  price
  rawPrice
  sellerType
  attachment(showForbiddenImage: $showForbiddenImage) {
    ...PartialFile
    __typename
  }
  isAttachmentsForbidden
  user {
    ...UserItemEdgeNode
    __typename
  }
  game {
    name
    __typename
  }
  category {
    name
    __typename
  }
  approvalDate
  priorityPosition
  createdAt
  viewsCounter
  dealsCounter
  feeMultiplier
  isAutomated
  __typename
}

fragment RegularTransaction on Transaction {
  id
  operation
  direction
  providerId
  provider {
    ...RegularTransactionProvider
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  creator {
    ...RegularUserFragment
    __typename
  }
  status
  statusDescription
  statusExpirationDate
  value
  fee
  createdAt
  props {
    ...RegularTransactionProps
    __typename
  }
  verifiedAt
  verifiedBy {
    ...UserEdgeNode
    __typename
  }
  completedBy {
    ...UserEdgeNode
    __typename
  }
  paymentMethodId
  completedAt
  isSuspicious
  spbBankName
  autoClaimedAt
  __typename
}

fragment RegularTransactionProvider on TransactionProvider {
  id
  name
  fee
  minFeeAmount
  description
  account {
    ...RegularTransactionProviderAccount
    __typename
  }
  props {
    ...TransactionProviderPropsFragment
    __typename
  }
  limits {
    ...ProviderLimits
    __typename
  }
  paymentMethods {
    ...TransactionPaymentMethod
    __typename
  }
  __typename
}

fragment RegularTransactionProviderAccount on TransactionProviderAccount {
  id
  value
  userId
  providerId
  paymentMethodId
  __typename
}

fragment TransactionProviderPropsFragment on TransactionProviderPropsFragment {
  requiredUserData {
    ...TransactionProviderRequiredUserData
    __typename
  }
  tooltip
  __typename
}

fragment TransactionProviderRequiredUserData on TransactionProviderRequiredUserData {
  email
  phoneNumber
  eripAccountNumber
  __typename
}

fragment ProviderLimits on ProviderLimits {
  incoming {
    ...ProviderLimitRange
    __typename
  }
  outgoing {
    ...ProviderLimitRange
    __typename
  }
  __typename
}

fragment ProviderLimitRange on ProviderLimitRange {
  min
  max
  __typename
}

fragment TransactionPaymentMethod on TransactionPaymentMethod {
  id
  name
  fee
  providerId
  account {
    ...RegularTransactionProviderAccount
    __typename
  }
  props {
    ...TransactionProviderPropsFragment
    __typename
  }
  limits {
    ...ProviderLimits
    __typename
  }
  __typename
}

fragment RegularTransactionProps on TransactionPropsFragment {
  creatorId
  dealId
  paidFromPendingIncome
  paymentURL
  successURL
  fee
  paymentAccount {
    id
    value
    __typename
  }
  paymentGateway
  alreadySpent
  exchangeRate
  amountAfterConversionRub
  amountAfterConversionUsdt
  fragmentUsername
  userData {
    account
    email
    ipAddress
    phoneNumber
    __typename
  }
  __typename
}

fragment ChatMessageButton on ChatMessageButton {
  type
  url
  text
  __typename
}

fragment RegularFile on File {
  id
  url
  filename
  mime
  __typename
}
""",
    'uploadChatImageIntoTemporaryStore': """
mutation uploadChatImageIntoTemporaryStore($file: Upload!, $input: UploadTemporaryAttachmentInput!) {
  uploadChatImageIntoTemporaryStore(file: $file, input: $input) {
    expiresAt
    id
    url
    chatId
    clientAttachmentId
    __typename
  }
}
""",
    'createItem': """
mutation createItem($input: CreateItemInput!, $attachments: [Upload!], $showForbiddenImage: Boolean) {
  createItem(input: $input, attachments: $attachments) {
    ...RegularItem
    __typename
  }
}

fragment RegularItem on Item {
  ...RegularMyItem
  ...RegularForeignItem
  __typename
}

fragment RegularMyItem on MyItem {
  ...ItemFields
  prevPrice
  priority
  sequence
  priorityPrice
  statusExpirationDate
  comment
  viewsCounter
  dealsCounter
  statusDescription
  editable
  statusPayment {
    ...StatusPaymentTransaction
    __typename
  }
  moderator {
    id
    username
    __typename
  }
  approvalDate
  deletedAt
  createdAt
  updatedAt
  mayBePublished
  prevFeeMultiplier
  sellerNotifiedAboutFeeChange
  postModerationCheckedAt
  __typename
}

fragment ItemFields on Item {
  id
  slug
  name
  description
  rawPrice
  price
  attributes
  status
  priorityPosition
  sellerType
  feeMultiplier
  user {
    ...ItemUser
    __typename
  }
  buyer {
    ...ItemUser
    __typename
  }
  attachments(showForbiddenImage: $showForbiddenImage) {
    ...PartialFile
    __typename
  }
  isAutomated
  isAttachmentsForbidden
  category {
    ...RegularGameCategory
    __typename
  }
  game {
    ...RegularGameProfile
    __typename
  }
  comment
  dataFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  obtainingType {
    ...GameCategoryObtainingType
    __typename
  }
  __typename
}

fragment ItemUser on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment RegularGameCategory on GameCategory {
  id
  slug
  name
  categoryId
  gameId
  obtaining
  options {
    ...RegularGameCategoryOption
    __typename
  }
  props {
    ...GameCategoryProps
    __typename
  }
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  useCustomObtaining
  autoConfirmPeriod
  autoModerationMode
  agreements {
    ...RegularGameCategoryAgreement
    __typename
  }
  feeMultiplier
  __typename
}

fragment RegularGameCategoryOption on GameCategoryOption {
  id
  group
  label
  type
  field
  value
  valueRangeLimit {
    min
    max
    __typename
  }
  multiple
  __typename
}

fragment GameCategoryProps on GameCategoryPropsObjectType {
  minTestimonials
  minTestimonialsForSeller
  __typename
}

fragment RegularGameCategoryAgreement on GameCategoryAgreement {
  description
  gameCategoryId
  gameCategoryObtainingTypeId
  iconType
  id
  sequence
  __typename
}

fragment RegularGameProfile on GameProfile {
  id
  name
  type
  slug
  logo {
    ...PartialFile
    __typename
  }
  __typename
}

fragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {
  id
  label
  type
  inputType
  copyable
  hidden
  required
  value
  __typename
}

fragment GameCategoryObtainingType on GameCategoryObtainingType {
  id
  name
  description
  gameCategoryId
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  sequence
  feeMultiplier
  agreements {
    ...MinimalGameCategoryAgreement
    __typename
  }
  props {
    minTestimonialsForSeller
    __typename
  }
  __typename
}

fragment MinimalGameCategoryAgreement on GameCategoryAgreement {
  description
  iconType
  id
  sequence
  __typename
}

fragment StatusPaymentTransaction on Transaction {
  id
  operation
  direction
  providerId
  status
  statusDescription
  statusExpirationDate
  value
  props {
    paymentURL
    __typename
  }
  __typename
}

fragment RegularForeignItem on ForeignItem {
  ...ItemFields
  postModerationCheckedAt
  __typename
}
""",
    'updateItem': """
mutation updateItem($input: UpdateItemInput!, $addedAttachments: [Upload!], $showForbiddenImage: Boolean) {
  updateItem(input: $input, addedAttachments: $addedAttachments) {
    ...RegularItem
    __typename
  }
}

fragment RegularItem on Item {
  ...RegularMyItem
  ...RegularForeignItem
  __typename
}

fragment RegularMyItem on MyItem {
  ...ItemFields
  prevPrice
  priority
  sequence
  priorityPrice
  statusExpirationDate
  comment
  viewsCounter
  dealsCounter
  statusDescription
  editable
  statusPayment {
    ...StatusPaymentTransaction
    __typename
  }
  moderator {
    id
    username
    __typename
  }
  approvalDate
  deletedAt
  createdAt
  updatedAt
  mayBePublished
  prevFeeMultiplier
  sellerNotifiedAboutFeeChange
  postModerationCheckedAt
  __typename
}

fragment ItemFields on Item {
  id
  slug
  name
  description
  rawPrice
  price
  attributes
  status
  priorityPosition
  sellerType
  feeMultiplier
  user {
    ...ItemUser
    __typename
  }
  buyer {
    ...ItemUser
    __typename
  }
  attachments(showForbiddenImage: $showForbiddenImage) {
    ...PartialFile
    __typename
  }
  isAutomated
  isAttachmentsForbidden
  category {
    ...RegularGameCategory
    __typename
  }
  game {
    ...RegularGameProfile
    __typename
  }
  comment
  dataFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  obtainingType {
    ...GameCategoryObtainingType
    __typename
  }
  __typename
}

fragment ItemUser on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment RegularGameCategory on GameCategory {
  id
  slug
  name
  categoryId
  gameId
  obtaining
  options {
    ...RegularGameCategoryOption
    __typename
  }
  props {
    ...GameCategoryProps
    __typename
  }
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  useCustomObtaining
  autoConfirmPeriod
  autoModerationMode
  agreements {
    ...RegularGameCategoryAgreement
    __typename
  }
  feeMultiplier
  __typename
}

fragment RegularGameCategoryOption on GameCategoryOption {
  id
  group
  label
  type
  field
  value
  valueRangeLimit {
    min
    max
    __typename
  }
  multiple
  __typename
}

fragment GameCategoryProps on GameCategoryPropsObjectType {
  minTestimonials
  minTestimonialsForSeller
  __typename
}

fragment RegularGameCategoryAgreement on GameCategoryAgreement {
  description
  gameCategoryId
  gameCategoryObtainingTypeId
  iconType
  id
  sequence
  __typename
}

fragment RegularGameProfile on GameProfile {
  id
  name
  type
  slug
  logo {
    ...PartialFile
    __typename
  }
  __typename
}

fragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {
  id
  label
  type
  inputType
  copyable
  hidden
  required
  value
  __typename
}

fragment GameCategoryObtainingType on GameCategoryObtainingType {
  id
  name
  description
  gameCategoryId
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  sequence
  feeMultiplier
  agreements {
    ...MinimalGameCategoryAgreement
    __typename
  }
  props {
    minTestimonialsForSeller
    __typename
  }
  __typename
}

fragment MinimalGameCategoryAgreement on GameCategoryAgreement {
  description
  iconType
  id
  sequence
  __typename
}

fragment StatusPaymentTransaction on Transaction {
  id
  operation
  direction
  providerId
  status
  statusDescription
  statusExpirationDate
  value
  props {
    paymentURL
    __typename
  }
  __typename
}

fragment RegularForeignItem on ForeignItem {
  ...ItemFields
  postModerationCheckedAt
  __typename
}
""",
    'removeItem': """
mutation removeItem($id: UUID!, $showForbiddenImage: Boolean) {
  removeItem(id: $id) {
    ...RegularItem
    __typename
  }
}

fragment RegularItem on Item {
  ...RegularMyItem
  ...RegularForeignItem
  __typename
}

fragment RegularMyItem on MyItem {
  ...ItemFields
  prevPrice
  priority
  sequence
  priorityPrice
  statusExpirationDate
  comment
  viewsCounter
  dealsCounter
  statusDescription
  editable
  statusPayment {
    ...StatusPaymentTransaction
    __typename
  }
  moderator {
    id
    username
    __typename
  }
  approvalDate
  deletedAt
  createdAt
  updatedAt
  mayBePublished
  prevFeeMultiplier
  sellerNotifiedAboutFeeChange
  postModerationCheckedAt
  __typename
}

fragment ItemFields on Item {
  id
  slug
  name
  description
  rawPrice
  price
  attributes
  status
  priorityPosition
  sellerType
  feeMultiplier
  user {
    ...ItemUser
    __typename
  }
  buyer {
    ...ItemUser
    __typename
  }
  attachments(showForbiddenImage: $showForbiddenImage) {
    ...PartialFile
    __typename
  }
  isAutomated
  isAttachmentsForbidden
  category {
    ...RegularGameCategory
    __typename
  }
  game {
    ...RegularGameProfile
    __typename
  }
  comment
  dataFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  obtainingType {
    ...GameCategoryObtainingType
    __typename
  }
  __typename
}

fragment ItemUser on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment RegularGameCategory on GameCategory {
  id
  slug
  name
  categoryId
  gameId
  obtaining
  options {
    ...RegularGameCategoryOption
    __typename
  }
  props {
    ...GameCategoryProps
    __typename
  }
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  useCustomObtaining
  autoConfirmPeriod
  autoModerationMode
  agreements {
    ...RegularGameCategoryAgreement
    __typename
  }
  feeMultiplier
  __typename
}

fragment RegularGameCategoryOption on GameCategoryOption {
  id
  group
  label
  type
  field
  value
  valueRangeLimit {
    min
    max
    __typename
  }
  multiple
  __typename
}

fragment GameCategoryProps on GameCategoryPropsObjectType {
  minTestimonials
  minTestimonialsForSeller
  __typename
}

fragment RegularGameCategoryAgreement on GameCategoryAgreement {
  description
  gameCategoryId
  gameCategoryObtainingTypeId
  iconType
  id
  sequence
  __typename
}

fragment RegularGameProfile on GameProfile {
  id
  name
  type
  slug
  logo {
    ...PartialFile
    __typename
  }
  __typename
}

fragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {
  id
  label
  type
  inputType
  copyable
  hidden
  required
  value
  __typename
}

fragment GameCategoryObtainingType on GameCategoryObtainingType {
  id
  name
  description
  gameCategoryId
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  sequence
  feeMultiplier
  agreements {
    ...MinimalGameCategoryAgreement
    __typename
  }
  props {
    minTestimonialsForSeller
    __typename
  }
  __typename
}

fragment MinimalGameCategoryAgreement on GameCategoryAgreement {
  description
  iconType
  id
  sequence
  __typename
}

fragment StatusPaymentTransaction on Transaction {
  id
  operation
  direction
  providerId
  status
  statusDescription
  statusExpirationDate
  value
  props {
    paymentURL
    __typename
  }
  __typename
}

fragment RegularForeignItem on ForeignItem {
  ...ItemFields
  postModerationCheckedAt
  __typename
}
""",
    'publishItem': """
mutation publishItem($input: PublishItemInput!, $showForbiddenImage: Boolean) {
  publishItem(input: $input) {
    ...RegularItem
    __typename
  }
}

fragment RegularItem on Item {
  ...RegularMyItem
  ...RegularForeignItem
  __typename
}

fragment RegularMyItem on MyItem {
  ...ItemFields
  prevPrice
  priority
  sequence
  priorityPrice
  statusExpirationDate
  comment
  viewsCounter
  dealsCounter
  statusDescription
  editable
  statusPayment {
    ...StatusPaymentTransaction
    __typename
  }
  moderator {
    id
    username
    __typename
  }
  approvalDate
  deletedAt
  createdAt
  updatedAt
  mayBePublished
  prevFeeMultiplier
  sellerNotifiedAboutFeeChange
  postModerationCheckedAt
  __typename
}

fragment ItemFields on Item {
  id
  slug
  name
  description
  rawPrice
  price
  attributes
  status
  priorityPosition
  sellerType
  feeMultiplier
  user {
    ...ItemUser
    __typename
  }
  buyer {
    ...ItemUser
    __typename
  }
  attachments(showForbiddenImage: $showForbiddenImage) {
    ...PartialFile
    __typename
  }
  isAutomated
  isAttachmentsForbidden
  category {
    ...RegularGameCategory
    __typename
  }
  game {
    ...RegularGameProfile
    __typename
  }
  comment
  dataFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  obtainingType {
    ...GameCategoryObtainingType
    __typename
  }
  __typename
}

fragment ItemUser on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment RegularGameCategory on GameCategory {
  id
  slug
  name
  categoryId
  gameId
  obtaining
  options {
    ...RegularGameCategoryOption
    __typename
  }
  props {
    ...GameCategoryProps
    __typename
  }
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  useCustomObtaining
  autoConfirmPeriod
  autoModerationMode
  agreements {
    ...RegularGameCategoryAgreement
    __typename
  }
  feeMultiplier
  __typename
}

fragment RegularGameCategoryOption on GameCategoryOption {
  id
  group
  label
  type
  field
  value
  valueRangeLimit {
    min
    max
    __typename
  }
  multiple
  __typename
}

fragment GameCategoryProps on GameCategoryPropsObjectType {
  minTestimonials
  minTestimonialsForSeller
  __typename
}

fragment RegularGameCategoryAgreement on GameCategoryAgreement {
  description
  gameCategoryId
  gameCategoryObtainingTypeId
  iconType
  id
  sequence
  __typename
}

fragment RegularGameProfile on GameProfile {
  id
  name
  type
  slug
  logo {
    ...PartialFile
    __typename
  }
  __typename
}

fragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {
  id
  label
  type
  inputType
  copyable
  hidden
  required
  value
  __typename
}

fragment GameCategoryObtainingType on GameCategoryObtainingType {
  id
  name
  description
  gameCategoryId
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  sequence
  feeMultiplier
  agreements {
    ...MinimalGameCategoryAgreement
    __typename
  }
  props {
    minTestimonialsForSeller
    __typename
  }
  __typename
}

fragment MinimalGameCategoryAgreement on GameCategoryAgreement {
  description
  iconType
  id
  sequence
  __typename
}

fragment StatusPaymentTransaction on Transaction {
  id
  operation
  direction
  providerId
  status
  statusDescription
  statusExpirationDate
  value
  props {
    paymentURL
    __typename
  }
  __typename
}

fragment RegularForeignItem on ForeignItem {
  ...ItemFields
  postModerationCheckedAt
  __typename
}
""",
    'increaseItemPriorityStatus': """
mutation increaseItemPriorityStatus($input: PublishItemInput!, $showForbiddenImage: Boolean) {
  increaseItemPriorityStatus(input: $input) {
    ...RegularItem
    __typename
  }
}

fragment RegularItem on Item {
  ...RegularMyItem
  ...RegularForeignItem
  __typename
}

fragment RegularMyItem on MyItem {
  ...ItemFields
  prevPrice
  priority
  sequence
  priorityPrice
  statusExpirationDate
  comment
  viewsCounter
  dealsCounter
  statusDescription
  editable
  statusPayment {
    ...StatusPaymentTransaction
    __typename
  }
  moderator {
    id
    username
    __typename
  }
  approvalDate
  deletedAt
  createdAt
  updatedAt
  mayBePublished
  prevFeeMultiplier
  sellerNotifiedAboutFeeChange
  postModerationCheckedAt
  __typename
}

fragment ItemFields on Item {
  id
  slug
  name
  description
  rawPrice
  price
  attributes
  status
  priorityPosition
  sellerType
  feeMultiplier
  user {
    ...ItemUser
    __typename
  }
  buyer {
    ...ItemUser
    __typename
  }
  attachments(showForbiddenImage: $showForbiddenImage) {
    ...PartialFile
    __typename
  }
  isAutomated
  isAttachmentsForbidden
  category {
    ...RegularGameCategory
    __typename
  }
  game {
    ...RegularGameProfile
    __typename
  }
  comment
  dataFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  obtainingType {
    ...GameCategoryObtainingType
    __typename
  }
  __typename
}

fragment ItemUser on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment RegularGameCategory on GameCategory {
  id
  slug
  name
  categoryId
  gameId
  obtaining
  options {
    ...RegularGameCategoryOption
    __typename
  }
  props {
    ...GameCategoryProps
    __typename
  }
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  useCustomObtaining
  autoConfirmPeriod
  autoModerationMode
  agreements {
    ...RegularGameCategoryAgreement
    __typename
  }
  feeMultiplier
  __typename
}

fragment RegularGameCategoryOption on GameCategoryOption {
  id
  group
  label
  type
  field
  value
  valueRangeLimit {
    min
    max
    __typename
  }
  multiple
  __typename
}

fragment GameCategoryProps on GameCategoryPropsObjectType {
  minTestimonials
  minTestimonialsForSeller
  __typename
}

fragment RegularGameCategoryAgreement on GameCategoryAgreement {
  description
  gameCategoryId
  gameCategoryObtainingTypeId
  iconType
  id
  sequence
  __typename
}

fragment RegularGameProfile on GameProfile {
  id
  name
  type
  slug
  logo {
    ...PartialFile
    __typename
  }
  __typename
}

fragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {
  id
  label
  type
  inputType
  copyable
  hidden
  required
  value
  __typename
}

fragment GameCategoryObtainingType on GameCategoryObtainingType {
  id
  name
  description
  gameCategoryId
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  sequence
  feeMultiplier
  agreements {
    ...MinimalGameCategoryAgreement
    __typename
  }
  props {
    minTestimonialsForSeller
    __typename
  }
  __typename
}

fragment MinimalGameCategoryAgreement on GameCategoryAgreement {
  description
  iconType
  id
  sequence
  __typename
}

fragment StatusPaymentTransaction on Transaction {
  id
  operation
  direction
  providerId
  status
  statusDescription
  statusExpirationDate
  value
  props {
    paymentURL
    __typename
  }
  __typename
}

fragment RegularForeignItem on ForeignItem {
  ...ItemFields
  postModerationCheckedAt
  __typename
}
""",
    'updateDeal': """
mutation updateDeal($input: UpdateItemDealInput!, $showForbiddenImage: Boolean) {
  updateDeal(input: $input) {
    ...RegularItemDeal
    __typename
  }
}

fragment RegularItemDeal on ItemDeal {
  id
  status
  direction
  statusExpirationDate
  statusDescription
  obtaining
  hasProblem
  reportProblemEnabled
  completedBy {
    ...MinimalUserFragment
    __typename
  }
  props {
    ...ItemDealProps
    __typename
  }
  prevStatus
  completedAt
  createdAt
  logs {
    ...ItemLog
    __typename
  }
  transaction {
    ...ItemDealTransaction
    __typename
  }
  user {
    ...UserEdgeNode
    __typename
  }
  chat {
    ...RegularChatId
    __typename
  }
  item {
    ...PartialDealItem
    __typename
  }
  testimonial {
    ...RegularItemDealTestimonial
    __typename
  }
  obtainingFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  commentFromBuyer
  isAutomated
  __typename
}

fragment MinimalUserFragment on UserFragment {
  id
  username
  role
  __typename
}

fragment ItemDealProps on ItemDealProps {
  autoConfirmPeriod
  __typename
}

fragment ItemLog on ItemLog {
  id
  event
  createdAt
  user {
    ...UserEdgeNode
    __typename
  }
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment ItemDealTransaction on Transaction {
  id
  operation
  direction
  providerId
  status
  value
  createdAt
  paymentMethodId
  statusExpirationDate
  __typename
}

fragment RegularChatId on Chat {
  id
  __typename
}

fragment PartialDealItem on Item {
  ...PartialDealMyItem
  ...PartialDealForeignItem
  __typename
}

fragment PartialDealMyItem on MyItem {
  id
  slug
  priority
  status
  name
  price
  priorityPrice
  rawPrice
  statusExpirationDate
  sellerType
  approvalDate
  createdAt
  priorityPosition
  viewsCounter
  feeMultiplier
  comment
  attachments(showForbiddenImage: $showForbiddenImage) {
    ...RegularFile
    __typename
  }
  isAttachmentsForbidden
  user {
    ...UserEdgeNode
    __typename
  }
  game {
    ...RegularGameProfile
    __typename
  }
  category {
    ...MinimalGameCategory
    __typename
  }
  dataFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  obtainingType {
    ...MinimalGameCategoryObtainingType
    __typename
  }
  __typename
}

fragment RegularFile on File {
  id
  url
  filename
  mime
  __typename
}

fragment RegularGameProfile on GameProfile {
  id
  name
  type
  slug
  logo {
    ...PartialFile
    __typename
  }
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment MinimalGameCategory on GameCategory {
  id
  slug
  name
  __typename
}

fragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {
  id
  label
  type
  inputType
  copyable
  hidden
  required
  value
  __typename
}

fragment MinimalGameCategoryObtainingType on GameCategoryObtainingType {
  id
  name
  description
  gameCategoryId
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  sequence
  feeMultiplier
  props {
    minTestimonialsForSeller
    __typename
  }
  __typename
}

fragment PartialDealForeignItem on ForeignItem {
  id
  slug
  priority
  status
  name
  price
  rawPrice
  sellerType
  approvalDate
  priorityPosition
  createdAt
  viewsCounter
  feeMultiplier
  comment
  attachments(showForbiddenImage: $showForbiddenImage) {
    ...RegularFile
    __typename
  }
  isAttachmentsForbidden
  user {
    ...UserEdgeNode
    __typename
  }
  game {
    ...RegularGameProfile
    __typename
  }
  category {
    ...MinimalGameCategory
    __typename
  }
  dataFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  obtainingType {
    ...MinimalGameCategoryObtainingType
    __typename
  }
  __typename
}

fragment RegularItemDealTestimonial on Testimonial {
  id
  status
  text
  rating
  createdAt
  updatedAt
  creator {
    ...RegularUserFragment
    __typename
  }
  moderator {
    ...RegularUserFragment
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  __typename
}
""",
    'reportDealProblem': """
mutation reportDealProblem($input: ReportDealProblemInput!, $showForbiddenImage: Boolean) {
  reportDealProblem(input: $input) {
    ...RegularItemDeal
    __typename
  }
}

fragment RegularItemDeal on ItemDeal {
  id
  status
  direction
  statusExpirationDate
  statusDescription
  obtaining
  hasProblem
  reportProblemEnabled
  completedBy {
    ...MinimalUserFragment
    __typename
  }
  props {
    ...ItemDealProps
    __typename
  }
  prevStatus
  completedAt
  createdAt
  logs {
    ...ItemLog
    __typename
  }
  transaction {
    ...ItemDealTransaction
    __typename
  }
  user {
    ...UserEdgeNode
    __typename
  }
  chat {
    ...RegularChatId
    __typename
  }
  item {
    ...PartialDealItem
    __typename
  }
  testimonial {
    ...RegularItemDealTestimonial
    __typename
  }
  obtainingFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  commentFromBuyer
  isAutomated
  __typename
}

fragment MinimalUserFragment on UserFragment {
  id
  username
  role
  __typename
}

fragment ItemDealProps on ItemDealProps {
  autoConfirmPeriod
  __typename
}

fragment ItemLog on ItemLog {
  id
  event
  createdAt
  user {
    ...UserEdgeNode
    __typename
  }
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment ItemDealTransaction on Transaction {
  id
  operation
  direction
  providerId
  status
  value
  createdAt
  paymentMethodId
  statusExpirationDate
  __typename
}

fragment RegularChatId on Chat {
  id
  __typename
}

fragment PartialDealItem on Item {
  ...PartialDealMyItem
  ...PartialDealForeignItem
  __typename
}

fragment PartialDealMyItem on MyItem {
  id
  slug
  priority
  status
  name
  price
  priorityPrice
  rawPrice
  statusExpirationDate
  sellerType
  approvalDate
  createdAt
  priorityPosition
  viewsCounter
  feeMultiplier
  comment
  attachments(showForbiddenImage: $showForbiddenImage) {
    ...RegularFile
    __typename
  }
  isAttachmentsForbidden
  user {
    ...UserEdgeNode
    __typename
  }
  game {
    ...RegularGameProfile
    __typename
  }
  category {
    ...MinimalGameCategory
    __typename
  }
  dataFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  obtainingType {
    ...MinimalGameCategoryObtainingType
    __typename
  }
  __typename
}

fragment RegularFile on File {
  id
  url
  filename
  mime
  __typename
}

fragment RegularGameProfile on GameProfile {
  id
  name
  type
  slug
  logo {
    ...PartialFile
    __typename
  }
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment MinimalGameCategory on GameCategory {
  id
  slug
  name
  __typename
}

fragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {
  id
  label
  type
  inputType
  copyable
  hidden
  required
  value
  __typename
}

fragment MinimalGameCategoryObtainingType on GameCategoryObtainingType {
  id
  name
  description
  gameCategoryId
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  sequence
  feeMultiplier
  props {
    minTestimonialsForSeller
    __typename
  }
  __typename
}

fragment PartialDealForeignItem on ForeignItem {
  id
  slug
  priority
  status
  name
  price
  rawPrice
  sellerType
  approvalDate
  priorityPosition
  createdAt
  viewsCounter
  feeMultiplier
  comment
  attachments(showForbiddenImage: $showForbiddenImage) {
    ...RegularFile
    __typename
  }
  isAttachmentsForbidden
  user {
    ...UserEdgeNode
    __typename
  }
  game {
    ...RegularGameProfile
    __typename
  }
  category {
    ...MinimalGameCategory
    __typename
  }
  dataFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  obtainingType {
    ...MinimalGameCategoryObtainingType
    __typename
  }
  __typename
}

fragment RegularItemDealTestimonial on Testimonial {
  id
  status
  text
  rating
  createdAt
  updatedAt
  creator {
    ...RegularUserFragment
    __typename
  }
  moderator {
    ...RegularUserFragment
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  __typename
}
""",
    'chatUpdated': """
subscription chatUpdated($filter: ChatFilter, $showForbiddenImage: Boolean) {
  chatUpdated(filter: $filter) {
    ...ChatUpdatedFields
    __typename
  }
}

fragment ChatUpdatedFields on Chat {
  id
  unreadMessagesCounter
  isTextingAllowed
  lastMessage {
    ...LastChatMessageFields
    __typename
  }
  status
  startedAt
  finishedAt
  __typename
}

fragment LastChatMessageFields on ChatMessage {
  id
  text
  createdAt
  isRead
  isBulkMessaging
  event
  file {
    ...RegularFile
    __typename
  }
  user {
    ...ChatMessageUserFields
    __typename
  }
  eventByUser {
    ...ChatMessageUserFields
    __typename
  }
  eventToUser {
    ...ChatMessageUserFields
    __typename
  }
  deal {
    ...ChatMessageItemDeal
    __typename
  }
  __typename
}

fragment RegularFile on File {
  id
  url
  filename
  mime
  __typename
}

fragment ChatMessageUserFields on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment ChatMessageItemDeal on ItemDeal {
  id
  direction
  status
  statusDescription
  hasProblem
  user {
    ...ChatParticipant
    __typename
  }
  testimonial {
    ...ChatMessageDealTestimonial
    __typename
  }
  item {
    id
    name
    price
    slug
    rawPrice
    sellerType
    user {
      ...ChatParticipant
      __typename
    }
    category {
      id
      __typename
    }
    attachments(showForbiddenImage: $showForbiddenImage) {
      ...PartialFile
      __typename
    }
    isAttachmentsForbidden
    comment
    dataFields {
      ...GameCategoryDataFieldWithValue
      __typename
    }
    obtainingType {
      ...GameCategoryObtainingType
      __typename
    }
    __typename
  }
  obtainingFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  automationObtainingFields {
    ...ItemDealAutomationObtainingField
    __typename
  }
  chat {
    id
    type
    __typename
  }
  transaction {
    id
    statusExpirationDate
    __typename
  }
  statusExpirationDate
  commentFromBuyer
  gameCategoryWarnings {
    ...ItemDealWarningFragment
    __typename
  }
  obtainingTypeWarnings {
    ...ItemDealWarningFragment
    __typename
  }
  __typename
}

fragment ChatParticipant on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment ChatMessageDealTestimonial on Testimonial {
  id
  status
  text
  rating
  createdAt
  updatedAt
  creator {
    ...RegularUserFragment
    __typename
  }
  moderator {
    ...RegularUserFragment
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {
  id
  label
  type
  inputType
  copyable
  hidden
  required
  value
  __typename
}

fragment GameCategoryObtainingType on GameCategoryObtainingType {
  id
  name
  description
  gameCategoryId
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  sequence
  feeMultiplier
  agreements {
    ...MinimalGameCategoryAgreement
    __typename
  }
  props {
    minTestimonialsForSeller
    __typename
  }
  __typename
}

fragment MinimalGameCategoryAgreement on GameCategoryAgreement {
  description
  iconType
  id
  sequence
  __typename
}

fragment ItemDealAutomationObtainingField on AutomationObtainingFieldItemDeals {
  code
  value
  name
  __typename
}

fragment ItemDealWarningFragment on ItemDealWarning {
  id
  status
  title
  text
  __typename
}
""",
    'chatMarkedAsRead': """
subscription chatMarkedAsRead($filter: ChatFilter, $showForbiddenImage: Boolean) {
  chatMarkedAsRead(filter: $filter) {
    ...ChatUpdatedFields
    __typename
  }
}

fragment ChatUpdatedFields on Chat {
  id
  unreadMessagesCounter
  isTextingAllowed
  lastMessage {
    ...LastChatMessageFields
    __typename
  }
  status
  startedAt
  finishedAt
  __typename
}

fragment LastChatMessageFields on ChatMessage {
  id
  text
  createdAt
  isRead
  isBulkMessaging
  event
  file {
    ...RegularFile
    __typename
  }
  user {
    ...ChatMessageUserFields
    __typename
  }
  eventByUser {
    ...ChatMessageUserFields
    __typename
  }
  eventToUser {
    ...ChatMessageUserFields
    __typename
  }
  deal {
    ...ChatMessageItemDeal
    __typename
  }
  __typename
}

fragment RegularFile on File {
  id
  url
  filename
  mime
  __typename
}

fragment ChatMessageUserFields on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment ChatMessageItemDeal on ItemDeal {
  id
  direction
  status
  statusDescription
  hasProblem
  user {
    ...ChatParticipant
    __typename
  }
  testimonial {
    ...ChatMessageDealTestimonial
    __typename
  }
  item {
    id
    name
    price
    slug
    rawPrice
    sellerType
    user {
      ...ChatParticipant
      __typename
    }
    category {
      id
      __typename
    }
    attachments(showForbiddenImage: $showForbiddenImage) {
      ...PartialFile
      __typename
    }
    isAttachmentsForbidden
    comment
    dataFields {
      ...GameCategoryDataFieldWithValue
      __typename
    }
    obtainingType {
      ...GameCategoryObtainingType
      __typename
    }
    __typename
  }
  obtainingFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  automationObtainingFields {
    ...ItemDealAutomationObtainingField
    __typename
  }
  chat {
    id
    type
    __typename
  }
  transaction {
    id
    statusExpirationDate
    __typename
  }
  statusExpirationDate
  commentFromBuyer
  gameCategoryWarnings {
    ...ItemDealWarningFragment
    __typename
  }
  obtainingTypeWarnings {
    ...ItemDealWarningFragment
    __typename
  }
  __typename
}

fragment ChatParticipant on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment ChatMessageDealTestimonial on Testimonial {
  id
  status
  text
  rating
  createdAt
  updatedAt
  creator {
    ...RegularUserFragment
    __typename
  }
  moderator {
    ...RegularUserFragment
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {
  id
  label
  type
  inputType
  copyable
  hidden
  required
  value
  __typename
}

fragment GameCategoryObtainingType on GameCategoryObtainingType {
  id
  name
  description
  gameCategoryId
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  sequence
  feeMultiplier
  agreements {
    ...MinimalGameCategoryAgreement
    __typename
  }
  props {
    minTestimonialsForSeller
    __typename
  }
  __typename
}

fragment MinimalGameCategoryAgreement on GameCategoryAgreement {
  description
  iconType
  id
  sequence
  __typename
}

fragment ItemDealAutomationObtainingField on AutomationObtainingFieldItemDeals {
  code
  value
  name
  __typename
}

fragment ItemDealWarningFragment on ItemDealWarning {
  id
  status
  title
  text
  __typename
}
""",
    'userUpdated': """
subscription userUpdated($userId: UUID) {
  userUpdated(userId: $userId) {
    ...PartialUserProfile
    __typename
  }
}

fragment PartialUserProfile on UserProfile {
  __typename
  ...PartialUser
  ...PartialUserFragment
}

fragment PartialUser on User {
  id
  unreadChatsCounter
  __typename
}

fragment PartialUserFragment on UserFragment {
  id
  __typename
}
""",
    'chatMessageCreated': """
subscription chatMessageCreated($filter: ChatMessageWSFilter!, $showForbiddenImage: Boolean) {
  chatMessageCreated(filter: $filter) {
    ...RegularChatMessage
    __typename
  }
}

fragment RegularChatMessage on ChatMessage {
  id
  text
  createdAt
  deletedAt
  isRead
  isSuspicious
  isBulkMessaging
  game {
    ...RegularGameProfile
    __typename
  }
  file {
    ...PartialFile
    __typename
  }
  user {
    ...ChatMessageUserFields
    __typename
  }
  deal {
    ...ChatMessageItemDeal
    __typename
  }
  item {
    ...ItemEdgeNode
    __typename
  }
  transaction {
    ...RegularTransaction
    __typename
  }
  moderator {
    ...UserEdgeNode
    __typename
  }
  eventByUser {
    ...ChatMessageUserFields
    __typename
  }
  eventToUser {
    ...ChatMessageUserFields
    __typename
  }
  isAutoResponse
  event
  buttons {
    ...ChatMessageButton
    __typename
  }
  images {
    ...RegularFile
    __typename
  }
  imageLinks
  uncensorInfo {
    count
    lastEvent {
      username
      createdAt
      __typename
    }
    __typename
  }
  plTokenAmount
  __typename
}

fragment RegularGameProfile on GameProfile {
  id
  name
  type
  slug
  logo {
    ...PartialFile
    __typename
  }
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment ChatMessageUserFields on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment ChatMessageItemDeal on ItemDeal {
  id
  direction
  status
  statusDescription
  hasProblem
  user {
    ...ChatParticipant
    __typename
  }
  testimonial {
    ...ChatMessageDealTestimonial
    __typename
  }
  item {
    id
    name
    price
    slug
    rawPrice
    sellerType
    user {
      ...ChatParticipant
      __typename
    }
    category {
      id
      __typename
    }
    attachments(showForbiddenImage: $showForbiddenImage) {
      ...PartialFile
      __typename
    }
    isAttachmentsForbidden
    comment
    dataFields {
      ...GameCategoryDataFieldWithValue
      __typename
    }
    obtainingType {
      ...GameCategoryObtainingType
      __typename
    }
    __typename
  }
  obtainingFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  automationObtainingFields {
    ...ItemDealAutomationObtainingField
    __typename
  }
  chat {
    id
    type
    __typename
  }
  transaction {
    id
    statusExpirationDate
    __typename
  }
  statusExpirationDate
  commentFromBuyer
  gameCategoryWarnings {
    ...ItemDealWarningFragment
    __typename
  }
  obtainingTypeWarnings {
    ...ItemDealWarningFragment
    __typename
  }
  __typename
}

fragment ChatParticipant on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment ChatMessageDealTestimonial on Testimonial {
  id
  status
  text
  rating
  createdAt
  updatedAt
  creator {
    ...RegularUserFragment
    __typename
  }
  moderator {
    ...RegularUserFragment
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  __typename
}

fragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {
  id
  label
  type
  inputType
  copyable
  hidden
  required
  value
  __typename
}

fragment GameCategoryObtainingType on GameCategoryObtainingType {
  id
  name
  description
  gameCategoryId
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  sequence
  feeMultiplier
  agreements {
    ...MinimalGameCategoryAgreement
    __typename
  }
  props {
    minTestimonialsForSeller
    __typename
  }
  __typename
}

fragment MinimalGameCategoryAgreement on GameCategoryAgreement {
  description
  iconType
  id
  sequence
  __typename
}

fragment ItemDealAutomationObtainingField on AutomationObtainingFieldItemDeals {
  code
  value
  name
  __typename
}

fragment ItemDealWarningFragment on ItemDealWarning {
  id
  status
  title
  text
  __typename
}

fragment ItemEdgeNode on ItemProfile {
  ...MyItemEdgeNode
  ...ForeignItemEdgeNode
  __typename
}

fragment MyItemEdgeNode on MyItemProfile {
  id
  slug
  priority
  status
  name
  price
  rawPrice
  statusExpirationDate
  sellerType
  attachment(showForbiddenImage: $showForbiddenImage) {
    ...PartialFile
    __typename
  }
  isAttachmentsForbidden
  user {
    ...UserItemEdgeNode
    __typename
  }
  game {
    name
    __typename
  }
  category {
    name
    __typename
  }
  approvalDate
  createdAt
  priorityPosition
  viewsCounter
  dealsCounter
  feeMultiplier
  isAutomated
  __typename
}

fragment UserItemEdgeNode on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment ForeignItemEdgeNode on ForeignItemProfile {
  id
  slug
  priority
  status
  name
  price
  rawPrice
  sellerType
  attachment(showForbiddenImage: $showForbiddenImage) {
    ...PartialFile
    __typename
  }
  isAttachmentsForbidden
  user {
    ...UserItemEdgeNode
    __typename
  }
  game {
    name
    __typename
  }
  category {
    name
    __typename
  }
  approvalDate
  priorityPosition
  createdAt
  viewsCounter
  dealsCounter
  feeMultiplier
  isAutomated
  __typename
}

fragment RegularTransaction on Transaction {
  id
  operation
  direction
  providerId
  provider {
    ...RegularTransactionProvider
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  creator {
    ...RegularUserFragment
    __typename
  }
  status
  statusDescription
  statusExpirationDate
  value
  fee
  createdAt
  props {
    ...RegularTransactionProps
    __typename
  }
  verifiedAt
  verifiedBy {
    ...UserEdgeNode
    __typename
  }
  completedBy {
    ...UserEdgeNode
    __typename
  }
  paymentMethodId
  completedAt
  isSuspicious
  spbBankName
  autoClaimedAt
  __typename
}

fragment RegularTransactionProvider on TransactionProvider {
  id
  name
  fee
  minFeeAmount
  description
  account {
    ...RegularTransactionProviderAccount
    __typename
  }
  props {
    ...TransactionProviderPropsFragment
    __typename
  }
  limits {
    ...ProviderLimits
    __typename
  }
  paymentMethods {
    ...TransactionPaymentMethod
    __typename
  }
  __typename
}

fragment RegularTransactionProviderAccount on TransactionProviderAccount {
  id
  value
  userId
  providerId
  paymentMethodId
  __typename
}

fragment TransactionProviderPropsFragment on TransactionProviderPropsFragment {
  requiredUserData {
    ...TransactionProviderRequiredUserData
    __typename
  }
  tooltip
  __typename
}

fragment TransactionProviderRequiredUserData on TransactionProviderRequiredUserData {
  email
  phoneNumber
  eripAccountNumber
  __typename
}

fragment ProviderLimits on ProviderLimits {
  incoming {
    ...ProviderLimitRange
    __typename
  }
  outgoing {
    ...ProviderLimitRange
    __typename
  }
  __typename
}

fragment ProviderLimitRange on ProviderLimitRange {
  min
  max
  __typename
}

fragment TransactionPaymentMethod on TransactionPaymentMethod {
  id
  name
  fee
  providerId
  account {
    ...RegularTransactionProviderAccount
    __typename
  }
  props {
    ...TransactionProviderPropsFragment
    __typename
  }
  limits {
    ...ProviderLimits
    __typename
  }
  __typename
}

fragment RegularTransactionProps on TransactionPropsFragment {
  creatorId
  dealId
  paidFromPendingIncome
  paymentURL
  successURL
  fee
  paymentAccount {
    id
    value
    __typename
  }
  paymentGateway
  alreadySpent
  exchangeRate
  amountAfterConversionRub
  amountAfterConversionUsdt
  fragmentUsername
  userData {
    account
    email
    ipAddress
    phoneNumber
    __typename
  }
  __typename
}

fragment ChatMessageButton on ChatMessageButton {
  type
  url
  text
  __typename
}

fragment RegularFile on File {
  id
  url
  filename
  mime
  __typename
}
""",
    'createDeal': """
mutation createDeal($input: CreateItemDealInput!) {
  createDeal(input: $input) {
    ...RegularTransaction
    __typename
  }
}

fragment RegularTransaction on Transaction {
  id
  operation
  direction
  providerId
  provider {
    ...RegularTransactionProvider
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  creator {
    ...RegularUserFragment
    __typename
  }
  status
  statusDescription
  statusExpirationDate
  value
  fee
  createdAt
  props {
    ...RegularTransactionProps
    __typename
  }
  verifiedAt
  verifiedBy {
    ...UserEdgeNode
    __typename
  }
  completedBy {
    ...UserEdgeNode
    __typename
  }
  paymentMethodId
  completedAt
  isSuspicious
  spbBankName
  autoClaimedAt
  __typename
}

fragment RegularTransactionProvider on TransactionProvider {
  id
  name
  fee
  minFeeAmount
  description
  account {
    ...RegularTransactionProviderAccount
    __typename
  }
  props {
    ...TransactionProviderPropsFragment
    __typename
  }
  limits {
    ...ProviderLimits
    __typename
  }
  paymentMethods {
    ...TransactionPaymentMethod
    __typename
  }
  __typename
}

fragment RegularTransactionProviderAccount on TransactionProviderAccount {
  id
  value
  userId
  providerId
  paymentMethodId
  __typename
}

fragment TransactionProviderPropsFragment on TransactionProviderPropsFragment {
  requiredUserData {
    ...TransactionProviderRequiredUserData
    __typename
  }
  tooltip
  __typename
}

fragment TransactionProviderRequiredUserData on TransactionProviderRequiredUserData {
  email
  phoneNumber
  eripAccountNumber
  __typename
}

fragment ProviderLimits on ProviderLimits {
  incoming {
    ...ProviderLimitRange
    __typename
  }
  outgoing {
    ...ProviderLimitRange
    __typename
  }
  __typename
}

fragment ProviderLimitRange on ProviderLimitRange {
  min
  max
  __typename
}

fragment TransactionPaymentMethod on TransactionPaymentMethod {
  id
  name
  fee
  providerId
  account {
    ...RegularTransactionProviderAccount
    __typename
  }
  props {
    ...TransactionProviderPropsFragment
    __typename
  }
  limits {
    ...ProviderLimits
    __typename
  }
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment RegularTransactionProps on TransactionPropsFragment {
  creatorId
  dealId
  paidFromPendingIncome
  paymentURL
  successURL
  fee
  paymentAccount {
    id
    value
    __typename
  }
  paymentGateway
  alreadySpent
  exchangeRate
  amountAfterConversionRub
  amountAfterConversionUsdt
  fragmentUsername
  userData {
    account
    email
    ipAddress
    phoneNumber
    __typename
  }
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}
""",
    'resolveDealProblem': """
mutation resolveDealProblem($input: ResolveDealProblemInput!, $showForbiddenImage: Boolean) {
  resolveDealProblem(input: $input) {
    ...RegularItemDeal
    __typename
  }
}

fragment RegularItemDeal on ItemDeal {
  id
  status
  direction
  statusExpirationDate
  statusDescription
  obtaining
  hasProblem
  reportProblemEnabled
  completedBy {
    ...MinimalUserFragment
    __typename
  }
  props {
    ...ItemDealProps
    __typename
  }
  prevStatus
  completedAt
  createdAt
  logs {
    ...ItemLog
    __typename
  }
  transaction {
    ...ItemDealTransaction
    __typename
  }
  user {
    ...UserEdgeNode
    __typename
  }
  chat {
    ...RegularChatId
    __typename
  }
  item {
    ...PartialDealItem
    __typename
  }
  testimonial {
    ...RegularItemDealTestimonial
    __typename
  }
  obtainingFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  commentFromBuyer
  isAutomated
  __typename
}

fragment MinimalUserFragment on UserFragment {
  id
  username
  role
  __typename
}

fragment ItemDealProps on ItemDealProps {
  autoConfirmPeriod
  __typename
}

fragment ItemLog on ItemLog {
  id
  event
  createdAt
  user {
    ...UserEdgeNode
    __typename
  }
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment ItemDealTransaction on Transaction {
  id
  operation
  direction
  providerId
  status
  value
  createdAt
  paymentMethodId
  statusExpirationDate
  __typename
}

fragment RegularChatId on Chat {
  id
  __typename
}

fragment PartialDealItem on Item {
  ...PartialDealMyItem
  ...PartialDealForeignItem
  __typename
}

fragment PartialDealMyItem on MyItem {
  id
  slug
  priority
  status
  name
  price
  priorityPrice
  rawPrice
  statusExpirationDate
  sellerType
  approvalDate
  createdAt
  priorityPosition
  viewsCounter
  feeMultiplier
  comment
  attachments(showForbiddenImage: $showForbiddenImage) {
    ...RegularFile
    __typename
  }
  isAttachmentsForbidden
  user {
    ...UserEdgeNode
    __typename
  }
  game {
    ...RegularGameProfile
    __typename
  }
  category {
    ...MinimalGameCategory
    __typename
  }
  dataFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  obtainingType {
    ...MinimalGameCategoryObtainingType
    __typename
  }
  __typename
}

fragment RegularFile on File {
  id
  url
  filename
  mime
  __typename
}

fragment RegularGameProfile on GameProfile {
  id
  name
  type
  slug
  logo {
    ...PartialFile
    __typename
  }
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment MinimalGameCategory on GameCategory {
  id
  slug
  name
  __typename
}

fragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {
  id
  label
  type
  inputType
  copyable
  hidden
  required
  value
  __typename
}

fragment MinimalGameCategoryObtainingType on GameCategoryObtainingType {
  id
  name
  description
  gameCategoryId
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  sequence
  feeMultiplier
  props {
    minTestimonialsForSeller
    __typename
  }
  __typename
}

fragment PartialDealForeignItem on ForeignItem {
  id
  slug
  priority
  status
  name
  price
  rawPrice
  sellerType
  approvalDate
  priorityPosition
  createdAt
  viewsCounter
  feeMultiplier
  comment
  attachments(showForbiddenImage: $showForbiddenImage) {
    ...RegularFile
    __typename
  }
  isAttachmentsForbidden
  user {
    ...UserEdgeNode
    __typename
  }
  game {
    ...RegularGameProfile
    __typename
  }
  category {
    ...MinimalGameCategory
    __typename
  }
  dataFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  obtainingType {
    ...MinimalGameCategoryObtainingType
    __typename
  }
  __typename
}

fragment RegularItemDealTestimonial on Testimonial {
  id
  status
  text
  rating
  createdAt
  updatedAt
  creator {
    ...RegularUserFragment
    __typename
  }
  moderator {
    ...RegularUserFragment
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  __typename
}
""",
    'createTestimonial': """
mutation createTestimonial($input: CreateTestimonialInput!, $showForbiddenImage: Boolean) {
  createTestimonial(input: $input) {
    ...RegularTestimonial
    __typename
  }
}

fragment RegularTestimonial on Testimonial {
  id
  status
  text
  rating
  createdAt
  updatedAt
  deal {
    ...RegularItemDealProfile
    __typename
  }
  creator {
    ...RegularUserFragment
    __typename
  }
  moderator {
    ...RegularUserFragment
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  __typename
}

fragment RegularItemDealProfile on ItemDealProfile {
  id
  direction
  status
  item {
    ...RegularItemProfile
    __typename
  }
  testimonial {
    ...TestimonialProfileFields
    __typename
  }
  __typename
}

fragment RegularItemProfile on ItemProfile {
  ...RegularMyItemProfile
  ...RegularForeignItemProfile
  __typename
}

fragment RegularMyItemProfile on MyItemProfile {
  id
  slug
  priority
  status
  name
  price
  rawPrice
  statusExpirationDate
  viewsCounter
  dealsCounter
  approvalDate
  createdAt
  sellerType
  attachment(showForbiddenImage: $showForbiddenImage) {
    ...PartialFile
    __typename
  }
  isAttachmentsForbidden
  game {
    ...RegularGameProfile
    __typename
  }
  category {
    ...RegularGameCategoryProfile
    __typename
  }
  user {
    ...ItemUser
    __typename
  }
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment RegularGameProfile on GameProfile {
  id
  name
  type
  slug
  logo {
    ...PartialFile
    __typename
  }
  __typename
}

fragment RegularGameCategoryProfile on GameCategoryProfile {
  id
  slug
  name
  __typename
}

fragment ItemUser on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment RegularForeignItemProfile on ForeignItemProfile {
  id
  slug
  priority
  name
  price
  rawPrice
  approvalDate
  createdAt
  sellerType
  attachment(showForbiddenImage: $showForbiddenImage) {
    ...RegularFile
    __typename
  }
  isAttachmentsForbidden
  game {
    ...RegularGameProfile
    __typename
  }
  category {
    ...RegularGameCategoryProfile
    __typename
  }
  user {
    ...ItemUser
    __typename
  }
  __typename
}

fragment RegularFile on File {
  id
  url
  filename
  mime
  __typename
}

fragment TestimonialProfileFields on TestimonialProfile {
  id
  status
  text
  rating
  createdAt
  __typename
}
""",
    'updateTestimonial': """
mutation updateTestimonial($input: UpdateTestimonialInput!, $showForbiddenImage: Boolean) {
  updateTestimonial(input: $input) {
    ...RegularTestimonial
    __typename
  }
}

fragment RegularTestimonial on Testimonial {
  id
  status
  text
  rating
  createdAt
  updatedAt
  deal {
    ...RegularItemDealProfile
    __typename
  }
  creator {
    ...RegularUserFragment
    __typename
  }
  moderator {
    ...RegularUserFragment
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  __typename
}

fragment RegularItemDealProfile on ItemDealProfile {
  id
  direction
  status
  item {
    ...RegularItemProfile
    __typename
  }
  testimonial {
    ...TestimonialProfileFields
    __typename
  }
  __typename
}

fragment RegularItemProfile on ItemProfile {
  ...RegularMyItemProfile
  ...RegularForeignItemProfile
  __typename
}

fragment RegularMyItemProfile on MyItemProfile {
  id
  slug
  priority
  status
  name
  price
  rawPrice
  statusExpirationDate
  viewsCounter
  dealsCounter
  approvalDate
  createdAt
  sellerType
  attachment(showForbiddenImage: $showForbiddenImage) {
    ...PartialFile
    __typename
  }
  isAttachmentsForbidden
  game {
    ...RegularGameProfile
    __typename
  }
  category {
    ...RegularGameCategoryProfile
    __typename
  }
  user {
    ...ItemUser
    __typename
  }
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment RegularGameProfile on GameProfile {
  id
  name
  type
  slug
  logo {
    ...PartialFile
    __typename
  }
  __typename
}

fragment RegularGameCategoryProfile on GameCategoryProfile {
  id
  slug
  name
  __typename
}

fragment ItemUser on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment RegularForeignItemProfile on ForeignItemProfile {
  id
  slug
  priority
  name
  price
  rawPrice
  approvalDate
  createdAt
  sellerType
  attachment(showForbiddenImage: $showForbiddenImage) {
    ...RegularFile
    __typename
  }
  isAttachmentsForbidden
  game {
    ...RegularGameProfile
    __typename
  }
  category {
    ...RegularGameCategoryProfile
    __typename
  }
  user {
    ...ItemUser
    __typename
  }
  __typename
}

fragment RegularFile on File {
  id
  url
  filename
  mime
  __typename
}

fragment TestimonialProfileFields on TestimonialProfile {
  id
  status
  text
  rating
  createdAt
  __typename
}
""",
    'removeTestimonial': """
mutation removeTestimonial($id: UUID!, $showForbiddenImage: Boolean) {
  removeTestimonial(id: $id) {
    ...RegularTestimonial
    __typename
  }
}

fragment RegularTestimonial on Testimonial {
  id
  status
  text
  rating
  createdAt
  updatedAt
  deal {
    ...RegularItemDealProfile
    __typename
  }
  creator {
    ...RegularUserFragment
    __typename
  }
  moderator {
    ...RegularUserFragment
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  __typename
}

fragment RegularItemDealProfile on ItemDealProfile {
  id
  direction
  status
  item {
    ...RegularItemProfile
    __typename
  }
  testimonial {
    ...TestimonialProfileFields
    __typename
  }
  __typename
}

fragment RegularItemProfile on ItemProfile {
  ...RegularMyItemProfile
  ...RegularForeignItemProfile
  __typename
}

fragment RegularMyItemProfile on MyItemProfile {
  id
  slug
  priority
  status
  name
  price
  rawPrice
  statusExpirationDate
  viewsCounter
  dealsCounter
  approvalDate
  createdAt
  sellerType
  attachment(showForbiddenImage: $showForbiddenImage) {
    ...PartialFile
    __typename
  }
  isAttachmentsForbidden
  game {
    ...RegularGameProfile
    __typename
  }
  category {
    ...RegularGameCategoryProfile
    __typename
  }
  user {
    ...ItemUser
    __typename
  }
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment RegularGameProfile on GameProfile {
  id
  name
  type
  slug
  logo {
    ...PartialFile
    __typename
  }
  __typename
}

fragment RegularGameCategoryProfile on GameCategoryProfile {
  id
  slug
  name
  __typename
}

fragment ItemUser on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment RegularForeignItemProfile on ForeignItemProfile {
  id
  slug
  priority
  name
  price
  rawPrice
  approvalDate
  createdAt
  sellerType
  attachment(showForbiddenImage: $showForbiddenImage) {
    ...RegularFile
    __typename
  }
  isAttachmentsForbidden
  game {
    ...RegularGameProfile
    __typename
  }
  category {
    ...RegularGameCategoryProfile
    __typename
  }
  user {
    ...ItemUser
    __typename
  }
  __typename
}

fragment RegularFile on File {
  id
  url
  filename
  mime
  __typename
}

fragment TestimonialProfileFields on TestimonialProfile {
  id
  status
  text
  rating
  createdAt
  __typename
}
""",
    'countDeals': """
query countDeals($filter: ItemDealFilter!) {
  countDeals(filter: $filter)
}
""",
    'chats': """
query chats($pagination: Pagination, $filter: ChatFilter, $hasSupportAccess: Boolean!) {
  chats(pagination: $pagination, filter: $filter) {
    edges {
      ...MinimalChatEdgeFields
      __typename
    }
    pageInfo {
      startCursor
      endCursor
      hasPreviousPage
      hasNextPage
      __typename
    }
    totalCount
    __typename
  }
}

fragment MinimalChatEdgeFields on ChatEdge {
  cursor
  node {
    ...MinimalChatEdgeNode
    __typename
  }
  __typename
}

fragment MinimalChatEdgeNode on Chat {
  id
  type
  status
  unreadMessagesCounter
  bookmarked
  lastMessage {
    ...MinimalLastChatMessageFields
    __typename
  }
  participants {
    ...ChatParticipant
    ...UserFragmentVipStatusFragment @include(if: $hasSupportAccess)
    __typename
  }
  __typename
}

fragment MinimalLastChatMessageFields on ChatMessage {
  id
  text
  createdAt
  isRead
  isBulkMessaging
  event
  file {
    ...PartialFile
    __typename
  }
  user {
    ...ChatMessageUserFields
    ...UserFragmentVipStatusFragment @include(if: $hasSupportAccess)
    __typename
  }
  eventByUser {
    id
    username
    __typename
  }
  eventToUser {
    id
    username
    __typename
  }
  deal {
    ...MinimalChatMessageItemDeal
    __typename
  }
  images {
    ...PartialFile
    __typename
  }
  imageLinks
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment ChatMessageUserFields on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment UserFragmentVipStatusFragment on UserFragment {
  isVip
  __typename
}

fragment MinimalChatMessageItemDeal on ItemDeal {
  id
  direction
  status
  statusDescription
  hasProblem
  user {
    ...MinimalChatParticipant
    __typename
  }
  item {
    id
    name
    slug
    sellerType
    user {
      ...MinimalChatParticipant
      __typename
    }
    __typename
  }
  __typename
}

fragment MinimalChatParticipant on UserFragment {
  id
  username
  role
  __typename
}

fragment ChatParticipant on UserFragment {
  ...RegularUserFragment
  __typename
}
""",
    'countChats': """
query countChats($filter: ChatFilter) {
  countChats(filter: $filter)
}
""",
    'updateChat': """
mutation updateChat($input: UpdateChatInput!, $showForbiddenImage: Boolean) {
  updateChat(input: $input) {
    id
    status
    finishedAt
    agent {
      ...ChatParticipant
      __typename
    }
    lastMessage {
      ...RegularChatMessage
      __typename
    }
    __typename
  }
}

fragment ChatParticipant on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment RegularChatMessage on ChatMessage {
  id
  text
  createdAt
  deletedAt
  isRead
  isSuspicious
  isBulkMessaging
  game {
    ...RegularGameProfile
    __typename
  }
  file {
    ...PartialFile
    __typename
  }
  user {
    ...ChatMessageUserFields
    __typename
  }
  deal {
    ...ChatMessageItemDeal
    __typename
  }
  item {
    ...ItemEdgeNode
    __typename
  }
  transaction {
    ...RegularTransaction
    __typename
  }
  moderator {
    ...UserEdgeNode
    __typename
  }
  eventByUser {
    ...ChatMessageUserFields
    __typename
  }
  eventToUser {
    ...ChatMessageUserFields
    __typename
  }
  isAutoResponse
  event
  buttons {
    ...ChatMessageButton
    __typename
  }
  images {
    ...RegularFile
    __typename
  }
  imageLinks
  uncensorInfo {
    count
    lastEvent {
      username
      createdAt
      __typename
    }
    __typename
  }
  plTokenAmount
  __typename
}

fragment RegularGameProfile on GameProfile {
  id
  name
  type
  slug
  logo {
    ...PartialFile
    __typename
  }
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment ChatMessageUserFields on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment ChatMessageItemDeal on ItemDeal {
  id
  direction
  status
  statusDescription
  hasProblem
  user {
    ...ChatParticipant
    __typename
  }
  testimonial {
    ...ChatMessageDealTestimonial
    __typename
  }
  item {
    id
    name
    price
    slug
    rawPrice
    sellerType
    user {
      ...ChatParticipant
      __typename
    }
    category {
      id
      __typename
    }
    attachments(showForbiddenImage: $showForbiddenImage) {
      ...PartialFile
      __typename
    }
    isAttachmentsForbidden
    comment
    dataFields {
      ...GameCategoryDataFieldWithValue
      __typename
    }
    obtainingType {
      ...GameCategoryObtainingType
      __typename
    }
    __typename
  }
  obtainingFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  automationObtainingFields {
    ...ItemDealAutomationObtainingField
    __typename
  }
  chat {
    id
    type
    __typename
  }
  transaction {
    id
    statusExpirationDate
    __typename
  }
  statusExpirationDate
  commentFromBuyer
  gameCategoryWarnings {
    ...ItemDealWarningFragment
    __typename
  }
  obtainingTypeWarnings {
    ...ItemDealWarningFragment
    __typename
  }
  __typename
}

fragment ChatMessageDealTestimonial on Testimonial {
  id
  status
  text
  rating
  createdAt
  updatedAt
  creator {
    ...RegularUserFragment
    __typename
  }
  moderator {
    ...RegularUserFragment
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  __typename
}

fragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {
  id
  label
  type
  inputType
  copyable
  hidden
  required
  value
  __typename
}

fragment GameCategoryObtainingType on GameCategoryObtainingType {
  id
  name
  description
  gameCategoryId
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  sequence
  feeMultiplier
  agreements {
    ...MinimalGameCategoryAgreement
    __typename
  }
  props {
    minTestimonialsForSeller
    __typename
  }
  __typename
}

fragment MinimalGameCategoryAgreement on GameCategoryAgreement {
  description
  iconType
  id
  sequence
  __typename
}

fragment ItemDealAutomationObtainingField on AutomationObtainingFieldItemDeals {
  code
  value
  name
  __typename
}

fragment ItemDealWarningFragment on ItemDealWarning {
  id
  status
  title
  text
  __typename
}

fragment ItemEdgeNode on ItemProfile {
  ...MyItemEdgeNode
  ...ForeignItemEdgeNode
  __typename
}

fragment MyItemEdgeNode on MyItemProfile {
  id
  slug
  priority
  status
  name
  price
  rawPrice
  statusExpirationDate
  sellerType
  attachment(showForbiddenImage: $showForbiddenImage) {
    ...PartialFile
    __typename
  }
  isAttachmentsForbidden
  user {
    ...UserItemEdgeNode
    __typename
  }
  game {
    name
    __typename
  }
  category {
    name
    __typename
  }
  approvalDate
  createdAt
  priorityPosition
  viewsCounter
  dealsCounter
  feeMultiplier
  isAutomated
  __typename
}

fragment UserItemEdgeNode on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment ForeignItemEdgeNode on ForeignItemProfile {
  id
  slug
  priority
  status
  name
  price
  rawPrice
  sellerType
  attachment(showForbiddenImage: $showForbiddenImage) {
    ...PartialFile
    __typename
  }
  isAttachmentsForbidden
  user {
    ...UserItemEdgeNode
    __typename
  }
  game {
    name
    __typename
  }
  category {
    name
    __typename
  }
  approvalDate
  priorityPosition
  createdAt
  viewsCounter
  dealsCounter
  feeMultiplier
  isAutomated
  __typename
}

fragment RegularTransaction on Transaction {
  id
  operation
  direction
  providerId
  provider {
    ...RegularTransactionProvider
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  creator {
    ...RegularUserFragment
    __typename
  }
  status
  statusDescription
  statusExpirationDate
  value
  fee
  createdAt
  props {
    ...RegularTransactionProps
    __typename
  }
  verifiedAt
  verifiedBy {
    ...UserEdgeNode
    __typename
  }
  completedBy {
    ...UserEdgeNode
    __typename
  }
  paymentMethodId
  completedAt
  isSuspicious
  spbBankName
  autoClaimedAt
  __typename
}

fragment RegularTransactionProvider on TransactionProvider {
  id
  name
  fee
  minFeeAmount
  description
  account {
    ...RegularTransactionProviderAccount
    __typename
  }
  props {
    ...TransactionProviderPropsFragment
    __typename
  }
  limits {
    ...ProviderLimits
    __typename
  }
  paymentMethods {
    ...TransactionPaymentMethod
    __typename
  }
  __typename
}

fragment RegularTransactionProviderAccount on TransactionProviderAccount {
  id
  value
  userId
  providerId
  paymentMethodId
  __typename
}

fragment TransactionProviderPropsFragment on TransactionProviderPropsFragment {
  requiredUserData {
    ...TransactionProviderRequiredUserData
    __typename
  }
  tooltip
  __typename
}

fragment TransactionProviderRequiredUserData on TransactionProviderRequiredUserData {
  email
  phoneNumber
  eripAccountNumber
  __typename
}

fragment ProviderLimits on ProviderLimits {
  incoming {
    ...ProviderLimitRange
    __typename
  }
  outgoing {
    ...ProviderLimitRange
    __typename
  }
  __typename
}

fragment ProviderLimitRange on ProviderLimitRange {
  min
  max
  __typename
}

fragment TransactionPaymentMethod on TransactionPaymentMethod {
  id
  name
  fee
  providerId
  account {
    ...RegularTransactionProviderAccount
    __typename
  }
  props {
    ...TransactionProviderPropsFragment
    __typename
  }
  limits {
    ...ProviderLimits
    __typename
  }
  __typename
}

fragment RegularTransactionProps on TransactionPropsFragment {
  creatorId
  dealId
  paidFromPendingIncome
  paymentURL
  successURL
  fee
  paymentAccount {
    id
    value
    __typename
  }
  paymentGateway
  alreadySpent
  exchangeRate
  amountAfterConversionRub
  amountAfterConversionUsdt
  fragmentUsername
  userData {
    account
    email
    ipAddress
    phoneNumber
    __typename
  }
  __typename
}

fragment ChatMessageButton on ChatMessageButton {
  type
  url
  text
  __typename
}

fragment RegularFile on File {
  id
  url
  filename
  mime
  __typename
}
""",
    'removeChatMessage': """
mutation removeChatMessage($id: UUID!) {
  removeChatMessage(id: $id) {
    id
    deletedAt
    moderator {
      ...UserEdgeNode
      __typename
    }
    __typename
  }
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}
""",
    'updateChatMessage': """
mutation updateChatMessage($input: UpdateChatMessageInput!, $showForbiddenImage: Boolean) {
  updateChatMessage(input: $input) {
    ...RegularChatMessage
    __typename
  }
}

fragment RegularChatMessage on ChatMessage {
  id
  text
  createdAt
  deletedAt
  isRead
  isSuspicious
  isBulkMessaging
  game {
    ...RegularGameProfile
    __typename
  }
  file {
    ...PartialFile
    __typename
  }
  user {
    ...ChatMessageUserFields
    __typename
  }
  deal {
    ...ChatMessageItemDeal
    __typename
  }
  item {
    ...ItemEdgeNode
    __typename
  }
  transaction {
    ...RegularTransaction
    __typename
  }
  moderator {
    ...UserEdgeNode
    __typename
  }
  eventByUser {
    ...ChatMessageUserFields
    __typename
  }
  eventToUser {
    ...ChatMessageUserFields
    __typename
  }
  isAutoResponse
  event
  buttons {
    ...ChatMessageButton
    __typename
  }
  images {
    ...RegularFile
    __typename
  }
  imageLinks
  uncensorInfo {
    count
    lastEvent {
      username
      createdAt
      __typename
    }
    __typename
  }
  plTokenAmount
  __typename
}

fragment RegularGameProfile on GameProfile {
  id
  name
  type
  slug
  logo {
    ...PartialFile
    __typename
  }
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment ChatMessageUserFields on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment ChatMessageItemDeal on ItemDeal {
  id
  direction
  status
  statusDescription
  hasProblem
  user {
    ...ChatParticipant
    __typename
  }
  testimonial {
    ...ChatMessageDealTestimonial
    __typename
  }
  item {
    id
    name
    price
    slug
    rawPrice
    sellerType
    user {
      ...ChatParticipant
      __typename
    }
    category {
      id
      __typename
    }
    attachments(showForbiddenImage: $showForbiddenImage) {
      ...PartialFile
      __typename
    }
    isAttachmentsForbidden
    comment
    dataFields {
      ...GameCategoryDataFieldWithValue
      __typename
    }
    obtainingType {
      ...GameCategoryObtainingType
      __typename
    }
    __typename
  }
  obtainingFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  automationObtainingFields {
    ...ItemDealAutomationObtainingField
    __typename
  }
  chat {
    id
    type
    __typename
  }
  transaction {
    id
    statusExpirationDate
    __typename
  }
  statusExpirationDate
  commentFromBuyer
  gameCategoryWarnings {
    ...ItemDealWarningFragment
    __typename
  }
  obtainingTypeWarnings {
    ...ItemDealWarningFragment
    __typename
  }
  __typename
}

fragment ChatParticipant on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment ChatMessageDealTestimonial on Testimonial {
  id
  status
  text
  rating
  createdAt
  updatedAt
  creator {
    ...RegularUserFragment
    __typename
  }
  moderator {
    ...RegularUserFragment
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  __typename
}

fragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {
  id
  label
  type
  inputType
  copyable
  hidden
  required
  value
  __typename
}

fragment GameCategoryObtainingType on GameCategoryObtainingType {
  id
  name
  description
  gameCategoryId
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  sequence
  feeMultiplier
  agreements {
    ...MinimalGameCategoryAgreement
    __typename
  }
  props {
    minTestimonialsForSeller
    __typename
  }
  __typename
}

fragment MinimalGameCategoryAgreement on GameCategoryAgreement {
  description
  iconType
  id
  sequence
  __typename
}

fragment ItemDealAutomationObtainingField on AutomationObtainingFieldItemDeals {
  code
  value
  name
  __typename
}

fragment ItemDealWarningFragment on ItemDealWarning {
  id
  status
  title
  text
  __typename
}

fragment ItemEdgeNode on ItemProfile {
  ...MyItemEdgeNode
  ...ForeignItemEdgeNode
  __typename
}

fragment MyItemEdgeNode on MyItemProfile {
  id
  slug
  priority
  status
  name
  price
  rawPrice
  statusExpirationDate
  sellerType
  attachment(showForbiddenImage: $showForbiddenImage) {
    ...PartialFile
    __typename
  }
  isAttachmentsForbidden
  user {
    ...UserItemEdgeNode
    __typename
  }
  game {
    name
    __typename
  }
  category {
    name
    __typename
  }
  approvalDate
  createdAt
  priorityPosition
  viewsCounter
  dealsCounter
  feeMultiplier
  isAutomated
  __typename
}

fragment UserItemEdgeNode on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment ForeignItemEdgeNode on ForeignItemProfile {
  id
  slug
  priority
  status
  name
  price
  rawPrice
  sellerType
  attachment(showForbiddenImage: $showForbiddenImage) {
    ...PartialFile
    __typename
  }
  isAttachmentsForbidden
  user {
    ...UserItemEdgeNode
    __typename
  }
  game {
    name
    __typename
  }
  category {
    name
    __typename
  }
  approvalDate
  priorityPosition
  createdAt
  viewsCounter
  dealsCounter
  feeMultiplier
  isAutomated
  __typename
}

fragment RegularTransaction on Transaction {
  id
  operation
  direction
  providerId
  provider {
    ...RegularTransactionProvider
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  creator {
    ...RegularUserFragment
    __typename
  }
  status
  statusDescription
  statusExpirationDate
  value
  fee
  createdAt
  props {
    ...RegularTransactionProps
    __typename
  }
  verifiedAt
  verifiedBy {
    ...UserEdgeNode
    __typename
  }
  completedBy {
    ...UserEdgeNode
    __typename
  }
  paymentMethodId
  completedAt
  isSuspicious
  spbBankName
  autoClaimedAt
  __typename
}

fragment RegularTransactionProvider on TransactionProvider {
  id
  name
  fee
  minFeeAmount
  description
  account {
    ...RegularTransactionProviderAccount
    __typename
  }
  props {
    ...TransactionProviderPropsFragment
    __typename
  }
  limits {
    ...ProviderLimits
    __typename
  }
  paymentMethods {
    ...TransactionPaymentMethod
    __typename
  }
  __typename
}

fragment RegularTransactionProviderAccount on TransactionProviderAccount {
  id
  value
  userId
  providerId
  paymentMethodId
  __typename
}

fragment TransactionProviderPropsFragment on TransactionProviderPropsFragment {
  requiredUserData {
    ...TransactionProviderRequiredUserData
    __typename
  }
  tooltip
  __typename
}

fragment TransactionProviderRequiredUserData on TransactionProviderRequiredUserData {
  email
  phoneNumber
  eripAccountNumber
  __typename
}

fragment ProviderLimits on ProviderLimits {
  incoming {
    ...ProviderLimitRange
    __typename
  }
  outgoing {
    ...ProviderLimitRange
    __typename
  }
  __typename
}

fragment ProviderLimitRange on ProviderLimitRange {
  min
  max
  __typename
}

fragment TransactionPaymentMethod on TransactionPaymentMethod {
  id
  name
  fee
  providerId
  account {
    ...RegularTransactionProviderAccount
    __typename
  }
  props {
    ...TransactionProviderPropsFragment
    __typename
  }
  limits {
    ...ProviderLimits
    __typename
  }
  __typename
}

fragment RegularTransactionProps on TransactionPropsFragment {
  creatorId
  dealId
  paidFromPendingIncome
  paymentURL
  successURL
  fee
  paymentAccount {
    id
    value
    __typename
  }
  paymentGateway
  alreadySpent
  exchangeRate
  amountAfterConversionRub
  amountAfterConversionUsdt
  fragmentUsername
  userData {
    account
    email
    ipAddress
    phoneNumber
    __typename
  }
  __typename
}

fragment ChatMessageButton on ChatMessageButton {
  type
  url
  text
  __typename
}

fragment RegularFile on File {
  id
  url
  filename
  mime
  __typename
}
""",
    'createChatBulkMessage': """
mutation createChatBulkMessage($input: CreateChatBulkMessageInput!, $file: Upload) {
  createChatBulkMessage(input: $input, file: $file) {
    ...ChatBulkMessage
    __typename
  }
}

fragment ChatBulkMessage on ChatBulkMessage {
  id
  text
  createdAt
  startedAt
  finishedAt
  sendAfter
  queueStatus
  stats {
    ...ChatBulkMessageStats
    __typename
  }
  buttons {
    ...ChatMessageButton
    __typename
  }
  admin {
    ...RegularUserFragment
    __typename
  }
  file {
    ...PartialFile
    __typename
  }
  game {
    ...RegularGame
    __typename
  }
  selector {
    audience
    otherSelections
    __typename
  }
  __typename
}

fragment ChatBulkMessageStats on ChatBulkMessageStats {
  completed
  total
  __typename
}

fragment ChatMessageButton on ChatMessageButton {
  type
  url
  text
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment RegularGame on Game {
  id
  slug
  name
  tags
  description
  type
  isNew
  logo {
    ...RegularFile
    __typename
  }
  banner {
    ...RegularFile
    __typename
  }
  categories {
    ...RegularGameCategory
    __typename
  }
  createdAt
  __typename
}

fragment RegularFile on File {
  id
  url
  filename
  mime
  __typename
}

fragment RegularGameCategory on GameCategory {
  id
  slug
  name
  categoryId
  gameId
  obtaining
  options {
    ...RegularGameCategoryOption
    __typename
  }
  props {
    ...GameCategoryProps
    __typename
  }
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  useCustomObtaining
  autoConfirmPeriod
  autoModerationMode
  agreements {
    ...RegularGameCategoryAgreement
    __typename
  }
  feeMultiplier
  __typename
}

fragment RegularGameCategoryOption on GameCategoryOption {
  id
  group
  label
  type
  field
  value
  valueRangeLimit {
    min
    max
    __typename
  }
  multiple
  __typename
}

fragment GameCategoryProps on GameCategoryPropsObjectType {
  minTestimonials
  minTestimonialsForSeller
  __typename
}

fragment RegularGameCategoryAgreement on GameCategoryAgreement {
  description
  gameCategoryId
  gameCategoryObtainingTypeId
  iconType
  id
  sequence
  __typename
}
""",
    'transactions': """
query transactions($pagination: Pagination, $filter: TransactionFilter!, $sort: Sort, $hasSupportAccess: Boolean!) {
  transactions(pagination: $pagination, filter: $filter, sort: $sort) {
    edges {
      cursor
      node {
        ...RegularTransaction
        user {
          ...RegularUserFragment
          ...UserFragmentVipStatusFragment @include(if: $hasSupportAccess)
          __typename
        }
        creator {
          ...RegularUserFragment
          ...UserFragmentVipStatusFragment @include(if: $hasSupportAccess)
          __typename
        }
        __typename
      }
      __typename
    }
    pageInfo {
      startCursor
      endCursor
      hasPreviousPage
      hasNextPage
      __typename
    }
    totalCount
    __typename
  }
}

fragment RegularTransaction on Transaction {
  id
  operation
  direction
  providerId
  provider {
    ...RegularTransactionProvider
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  creator {
    ...RegularUserFragment
    __typename
  }
  status
  statusDescription
  statusExpirationDate
  value
  fee
  createdAt
  props {
    ...RegularTransactionProps
    __typename
  }
  verifiedAt
  verifiedBy {
    ...UserEdgeNode
    __typename
  }
  completedBy {
    ...UserEdgeNode
    __typename
  }
  paymentMethodId
  completedAt
  isSuspicious
  spbBankName
  autoClaimedAt
  __typename
}

fragment RegularTransactionProvider on TransactionProvider {
  id
  name
  fee
  minFeeAmount
  description
  account {
    ...RegularTransactionProviderAccount
    __typename
  }
  props {
    ...TransactionProviderPropsFragment
    __typename
  }
  limits {
    ...ProviderLimits
    __typename
  }
  paymentMethods {
    ...TransactionPaymentMethod
    __typename
  }
  __typename
}

fragment RegularTransactionProviderAccount on TransactionProviderAccount {
  id
  value
  userId
  providerId
  paymentMethodId
  __typename
}

fragment TransactionProviderPropsFragment on TransactionProviderPropsFragment {
  requiredUserData {
    ...TransactionProviderRequiredUserData
    __typename
  }
  tooltip
  __typename
}

fragment TransactionProviderRequiredUserData on TransactionProviderRequiredUserData {
  email
  phoneNumber
  eripAccountNumber
  __typename
}

fragment ProviderLimits on ProviderLimits {
  incoming {
    ...ProviderLimitRange
    __typename
  }
  outgoing {
    ...ProviderLimitRange
    __typename
  }
  __typename
}

fragment ProviderLimitRange on ProviderLimitRange {
  min
  max
  __typename
}

fragment TransactionPaymentMethod on TransactionPaymentMethod {
  id
  name
  fee
  providerId
  account {
    ...RegularTransactionProviderAccount
    __typename
  }
  props {
    ...TransactionProviderPropsFragment
    __typename
  }
  limits {
    ...ProviderLimits
    __typename
  }
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment RegularTransactionProps on TransactionPropsFragment {
  creatorId
  dealId
  paidFromPendingIncome
  paymentURL
  successURL
  fee
  paymentAccount {
    id
    value
    __typename
  }
  paymentGateway
  alreadySpent
  exchangeRate
  amountAfterConversionRub
  amountAfterConversionUsdt
  fragmentUsername
  userData {
    account
    email
    ipAddress
    phoneNumber
    __typename
  }
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment UserFragmentVipStatusFragment on UserFragment {
  isVip
  __typename
}
""",
    'transaction': """
query transaction($id: UUID!) {
  transaction(id: $id) {
    ...RegularTransaction
    __typename
  }
}

fragment RegularTransaction on Transaction {
  id
  operation
  direction
  providerId
  provider {
    ...RegularTransactionProvider
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  creator {
    ...RegularUserFragment
    __typename
  }
  status
  statusDescription
  statusExpirationDate
  value
  fee
  createdAt
  props {
    ...RegularTransactionProps
    __typename
  }
  verifiedAt
  verifiedBy {
    ...UserEdgeNode
    __typename
  }
  completedBy {
    ...UserEdgeNode
    __typename
  }
  paymentMethodId
  completedAt
  isSuspicious
  spbBankName
  autoClaimedAt
  __typename
}

fragment RegularTransactionProvider on TransactionProvider {
  id
  name
  fee
  minFeeAmount
  description
  account {
    ...RegularTransactionProviderAccount
    __typename
  }
  props {
    ...TransactionProviderPropsFragment
    __typename
  }
  limits {
    ...ProviderLimits
    __typename
  }
  paymentMethods {
    ...TransactionPaymentMethod
    __typename
  }
  __typename
}

fragment RegularTransactionProviderAccount on TransactionProviderAccount {
  id
  value
  userId
  providerId
  paymentMethodId
  __typename
}

fragment TransactionProviderPropsFragment on TransactionProviderPropsFragment {
  requiredUserData {
    ...TransactionProviderRequiredUserData
    __typename
  }
  tooltip
  __typename
}

fragment TransactionProviderRequiredUserData on TransactionProviderRequiredUserData {
  email
  phoneNumber
  eripAccountNumber
  __typename
}

fragment ProviderLimits on ProviderLimits {
  incoming {
    ...ProviderLimitRange
    __typename
  }
  outgoing {
    ...ProviderLimitRange
    __typename
  }
  __typename
}

fragment ProviderLimitRange on ProviderLimitRange {
  min
  max
  __typename
}

fragment TransactionPaymentMethod on TransactionPaymentMethod {
  id
  name
  fee
  providerId
  account {
    ...RegularTransactionProviderAccount
    __typename
  }
  props {
    ...TransactionProviderPropsFragment
    __typename
  }
  limits {
    ...ProviderLimits
    __typename
  }
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment RegularTransactionProps on TransactionPropsFragment {
  creatorId
  dealId
  paidFromPendingIncome
  paymentURL
  successURL
  fee
  paymentAccount {
    id
    value
    __typename
  }
  paymentGateway
  alreadySpent
  exchangeRate
  amountAfterConversionRub
  amountAfterConversionUsdt
  fragmentUsername
  userData {
    account
    email
    ipAddress
    phoneNumber
    __typename
  }
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}
""",
    'payouts': """
query payouts($pagination: Pagination, $filter: PayoutFilter!) {
  payouts(pagination: $pagination, filter: $filter) {
    ...PayoutList
    __typename
  }
}

fragment PayoutList on PayoutList {
  edges {
    ...PayoutEdge
    __typename
  }
  pageInfo {
    ...PayoutPageInfo
    __typename
  }
  totalCount
  __typename
}

fragment PayoutEdge on PayoutEdge {
  cursor
  node {
    ...Payout
    __typename
  }
  __typename
}

fragment Payout on Payout {
  id
  status
  completedAt
  to
  ipAddress
  value
  remoteId
  paymentGateway
  providerId
  createdAt
  creator {
    ...UserEdgeNode
    __typename
  }
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment PayoutPageInfo on PayoutPageInfo {
  startCursor
  endCursor
  hasPreviousPage
  hasNextPage
  __typename
}
""",
    'requestWithdrawal': """
mutation requestWithdrawal($input: CreateWithdrawalTransactionInput!) {
  requestWithdrawal(input: $input) {
    ...RegularTransaction
    __typename
  }
}

fragment RegularTransaction on Transaction {
  id
  operation
  direction
  providerId
  provider {
    ...RegularTransactionProvider
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  creator {
    ...RegularUserFragment
    __typename
  }
  status
  statusDescription
  statusExpirationDate
  value
  fee
  createdAt
  props {
    ...RegularTransactionProps
    __typename
  }
  verifiedAt
  verifiedBy {
    ...UserEdgeNode
    __typename
  }
  completedBy {
    ...UserEdgeNode
    __typename
  }
  paymentMethodId
  completedAt
  isSuspicious
  spbBankName
  autoClaimedAt
  __typename
}

fragment RegularTransactionProvider on TransactionProvider {
  id
  name
  fee
  minFeeAmount
  description
  account {
    ...RegularTransactionProviderAccount
    __typename
  }
  props {
    ...TransactionProviderPropsFragment
    __typename
  }
  limits {
    ...ProviderLimits
    __typename
  }
  paymentMethods {
    ...TransactionPaymentMethod
    __typename
  }
  __typename
}

fragment RegularTransactionProviderAccount on TransactionProviderAccount {
  id
  value
  userId
  providerId
  paymentMethodId
  __typename
}

fragment TransactionProviderPropsFragment on TransactionProviderPropsFragment {
  requiredUserData {
    ...TransactionProviderRequiredUserData
    __typename
  }
  tooltip
  __typename
}

fragment TransactionProviderRequiredUserData on TransactionProviderRequiredUserData {
  email
  phoneNumber
  eripAccountNumber
  __typename
}

fragment ProviderLimits on ProviderLimits {
  incoming {
    ...ProviderLimitRange
    __typename
  }
  outgoing {
    ...ProviderLimitRange
    __typename
  }
  __typename
}

fragment ProviderLimitRange on ProviderLimitRange {
  min
  max
  __typename
}

fragment TransactionPaymentMethod on TransactionPaymentMethod {
  id
  name
  fee
  providerId
  account {
    ...RegularTransactionProviderAccount
    __typename
  }
  props {
    ...TransactionProviderPropsFragment
    __typename
  }
  limits {
    ...ProviderLimits
    __typename
  }
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment RegularTransactionProps on TransactionPropsFragment {
  creatorId
  dealId
  paidFromPendingIncome
  paymentURL
  successURL
  fee
  paymentAccount {
    id
    value
    __typename
  }
  paymentGateway
  alreadySpent
  exchangeRate
  amountAfterConversionRub
  amountAfterConversionUsdt
  fragmentUsername
  userData {
    account
    email
    ipAddress
    phoneNumber
    __typename
  }
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}
""",
    'createPayout': """
mutation createPayout($input: CreatePayoutInput!) {
  createPayout(input: $input) {
    ...Payout
    __typename
  }
}

fragment Payout on Payout {
  id
  status
  completedAt
  to
  ipAddress
  value
  remoteId
  paymentGateway
  providerId
  createdAt
  creator {
    ...UserEdgeNode
    __typename
  }
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}
""",
    'createPaymentURL': """
mutation createPaymentURL($input: CreateDepositTransactionInput!) {
  createPaymentURL(input: $input)
}
""",
    'verifiedCards': """
query verifiedCards($pagination: Pagination, $sort: Sort, $filter: CardFilter) {
  verifiedCards(filter: $filter, pagination: $pagination, sort: $sort) {
    edges {
      ...MinimalUserBankCardEdge
      __typename
    }
    pageInfo {
      startCursor
      endCursor
      hasPreviousPage
      hasNextPage
      __typename
    }
    totalCount
    __typename
  }
}

fragment MinimalUserBankCardEdge on UserBankCardEdge {
  cursor
  node {
    ...MinimalUserBankCard
    __typename
  }
  __typename
}

fragment MinimalUserBankCard on UserBankCard {
  id
  cardFirstSix
  cardLastFour
  cardType
  isChosen
  __typename
}
""",
    'setChosenCard': """
mutation setChosenCard($input: SetChosenCardInput!) {
  setChosenCard(input: $input)
}
""",
    'itemUpdated': """
subscription itemUpdated($filter: ItemFilter!, $showForbiddenImage: Boolean) {
  itemUpdated(filter: $filter) {
    ...RegularItem
    __typename
  }
}

fragment RegularItem on Item {
  ...RegularMyItem
  ...RegularForeignItem
  __typename
}

fragment RegularMyItem on MyItem {
  ...ItemFields
  prevPrice
  priority
  sequence
  priorityPrice
  statusExpirationDate
  comment
  viewsCounter
  dealsCounter
  statusDescription
  editable
  statusPayment {
    ...StatusPaymentTransaction
    __typename
  }
  moderator {
    id
    username
    __typename
  }
  approvalDate
  deletedAt
  createdAt
  updatedAt
  mayBePublished
  prevFeeMultiplier
  sellerNotifiedAboutFeeChange
  postModerationCheckedAt
  __typename
}

fragment ItemFields on Item {
  id
  slug
  name
  description
  rawPrice
  price
  attributes
  status
  priorityPosition
  sellerType
  feeMultiplier
  user {
    ...ItemUser
    __typename
  }
  buyer {
    ...ItemUser
    __typename
  }
  attachments(showForbiddenImage: $showForbiddenImage) {
    ...PartialFile
    __typename
  }
  isAutomated
  isAttachmentsForbidden
  category {
    ...RegularGameCategory
    __typename
  }
  game {
    ...RegularGameProfile
    __typename
  }
  comment
  dataFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  obtainingType {
    ...GameCategoryObtainingType
    __typename
  }
  __typename
}

fragment ItemUser on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment RegularGameCategory on GameCategory {
  id
  slug
  name
  categoryId
  gameId
  obtaining
  options {
    ...RegularGameCategoryOption
    __typename
  }
  props {
    ...GameCategoryProps
    __typename
  }
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  useCustomObtaining
  autoConfirmPeriod
  autoModerationMode
  agreements {
    ...RegularGameCategoryAgreement
    __typename
  }
  feeMultiplier
  __typename
}

fragment RegularGameCategoryOption on GameCategoryOption {
  id
  group
  label
  type
  field
  value
  valueRangeLimit {
    min
    max
    __typename
  }
  multiple
  __typename
}

fragment GameCategoryProps on GameCategoryPropsObjectType {
  minTestimonials
  minTestimonialsForSeller
  __typename
}

fragment RegularGameCategoryAgreement on GameCategoryAgreement {
  description
  gameCategoryId
  gameCategoryObtainingTypeId
  iconType
  id
  sequence
  __typename
}

fragment RegularGameProfile on GameProfile {
  id
  name
  type
  slug
  logo {
    ...PartialFile
    __typename
  }
  __typename
}

fragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {
  id
  label
  type
  inputType
  copyable
  hidden
  required
  value
  __typename
}

fragment GameCategoryObtainingType on GameCategoryObtainingType {
  id
  name
  description
  gameCategoryId
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  sequence
  feeMultiplier
  agreements {
    ...MinimalGameCategoryAgreement
    __typename
  }
  props {
    minTestimonialsForSeller
    __typename
  }
  __typename
}

fragment MinimalGameCategoryAgreement on GameCategoryAgreement {
  description
  iconType
  id
  sequence
  __typename
}

fragment StatusPaymentTransaction on Transaction {
  id
  operation
  direction
  providerId
  status
  statusDescription
  statusExpirationDate
  value
  props {
    paymentURL
    __typename
  }
  __typename
}

fragment RegularForeignItem on ForeignItem {
  ...ItemFields
  postModerationCheckedAt
  __typename
}
""",
    'itemCreated': """
subscription itemCreated($filter: ItemFilter!, $showForbiddenImage: Boolean) {
  itemCreated(filter: $filter) {
    ...RegularItem
    __typename
  }
}

fragment RegularItem on Item {
  ...RegularMyItem
  ...RegularForeignItem
  __typename
}

fragment RegularMyItem on MyItem {
  ...ItemFields
  prevPrice
  priority
  sequence
  priorityPrice
  statusExpirationDate
  comment
  viewsCounter
  dealsCounter
  statusDescription
  editable
  statusPayment {
    ...StatusPaymentTransaction
    __typename
  }
  moderator {
    id
    username
    __typename
  }
  approvalDate
  deletedAt
  createdAt
  updatedAt
  mayBePublished
  prevFeeMultiplier
  sellerNotifiedAboutFeeChange
  postModerationCheckedAt
  __typename
}

fragment ItemFields on Item {
  id
  slug
  name
  description
  rawPrice
  price
  attributes
  status
  priorityPosition
  sellerType
  feeMultiplier
  user {
    ...ItemUser
    __typename
  }
  buyer {
    ...ItemUser
    __typename
  }
  attachments(showForbiddenImage: $showForbiddenImage) {
    ...PartialFile
    __typename
  }
  isAutomated
  isAttachmentsForbidden
  category {
    ...RegularGameCategory
    __typename
  }
  game {
    ...RegularGameProfile
    __typename
  }
  comment
  dataFields {
    ...GameCategoryDataFieldWithValue
    __typename
  }
  obtainingType {
    ...GameCategoryObtainingType
    __typename
  }
  __typename
}

fragment ItemUser on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment RegularGameCategory on GameCategory {
  id
  slug
  name
  categoryId
  gameId
  obtaining
  options {
    ...RegularGameCategoryOption
    __typename
  }
  props {
    ...GameCategoryProps
    __typename
  }
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  useCustomObtaining
  autoConfirmPeriod
  autoModerationMode
  agreements {
    ...RegularGameCategoryAgreement
    __typename
  }
  feeMultiplier
  __typename
}

fragment RegularGameCategoryOption on GameCategoryOption {
  id
  group
  label
  type
  field
  value
  valueRangeLimit {
    min
    max
    __typename
  }
  multiple
  __typename
}

fragment GameCategoryProps on GameCategoryPropsObjectType {
  minTestimonials
  minTestimonialsForSeller
  __typename
}

fragment RegularGameCategoryAgreement on GameCategoryAgreement {
  description
  gameCategoryId
  gameCategoryObtainingTypeId
  iconType
  id
  sequence
  __typename
}

fragment RegularGameProfile on GameProfile {
  id
  name
  type
  slug
  logo {
    ...PartialFile
    __typename
  }
  __typename
}

fragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {
  id
  label
  type
  inputType
  copyable
  hidden
  required
  value
  __typename
}

fragment GameCategoryObtainingType on GameCategoryObtainingType {
  id
  name
  description
  gameCategoryId
  noCommentFromBuyer
  instructionForBuyer
  instructionForSeller
  sequence
  feeMultiplier
  agreements {
    ...MinimalGameCategoryAgreement
    __typename
  }
  props {
    minTestimonialsForSeller
    __typename
  }
  __typename
}

fragment MinimalGameCategoryAgreement on GameCategoryAgreement {
  description
  iconType
  id
  sequence
  __typename
}

fragment StatusPaymentTransaction on Transaction {
  id
  operation
  direction
  providerId
  status
  statusDescription
  statusExpirationDate
  value
  props {
    paymentURL
    __typename
  }
  __typename
}

fragment RegularForeignItem on ForeignItem {
  ...ItemFields
  postModerationCheckedAt
  __typename
}
""",
    'chatCreated': """
subscription chatCreated($filter: ChatFilter) {
  chatCreated(filter: $filter) {
    ...RegularChat
    __typename
  }
}

fragment RegularChat on Chat {
  id
  type
  unreadMessagesCounter
  bookmarked
  isTextingAllowed
  owner {
    ...ChatParticipant
    __typename
  }
  agent {
    ...ChatParticipant
    __typename
  }
  participants {
    ...ChatParticipant
    __typename
  }
  deals {
    ...ChatActiveItemDeal
    __typename
  }
  status
  startedAt
  finishedAt
  __typename
}

fragment ChatParticipant on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
  __typename
}

fragment ChatActiveItemDeal on ItemDealProfile {
  id
  direction
  status
  hasProblem
  testimonial {
    id
    rating
    __typename
  }
  item {
    ...ChatDealItemEdgeNode
    __typename
  }
  user {
    ...RegularUserFragment
    __typename
  }
  __typename
}

fragment ChatDealItemEdgeNode on ItemProfile {
  ...ChatDealMyItemEdgeNode
  ...ChatDealForeignItemEdgeNode
  __typename
}

fragment ChatDealMyItemEdgeNode on MyItemProfile {
  id
  slug
  priority
  status
  name
  price
  rawPrice
  statusExpirationDate
  sellerType
  attachment {
    ...PartialFile
    __typename
  }
  user {
    ...UserItemEdgeNode
    __typename
  }
  approvalDate
  createdAt
  priorityPosition
  feeMultiplier
  __typename
}

fragment PartialFile on File {
  id
  url
  __typename
}

fragment UserItemEdgeNode on UserFragment {
  ...UserEdgeNode
  __typename
}

fragment UserEdgeNode on UserFragment {
  ...RegularUserFragment
  __typename
}

fragment ChatDealForeignItemEdgeNode on ForeignItemProfile {
  id
  slug
  priority
  status
  name
  price
  rawPrice
  sellerType
  attachment {
    ...PartialFile
    __typename
  }
  user {
    ...UserItemEdgeNode
    __typename
  }
  approvalDate
  priorityPosition
  createdAt
  feeMultiplier
  __typename
}
""",
}

QUERY_TEXTS['items'] = """
query items($filter: ItemFilter, $pagination: Pagination, $sort: Sort, $showForbiddenImage: Boolean) {
  items(filter: $filter, pagination: $pagination, sort: $sort) {
    edges {
      ...ItemEdgeFields
    }
    pageInfo {
      startCursor
      endCursor
      hasPreviousPage
      hasNextPage
    }
    totalCount
  }
}

fragment ItemEdgeFields on ItemProfileEdge {
  cursor
  node {
    ... on ForeignItemProfile {
      id
      slug
      priority
      status
      name
      price
      rawPrice
      sellerType
      attachment {
        ...PartialFile
      }
      isAttachmentsForbidden
      user {
        ...RegularUserFragment
      }
      game {
        ...RegularGameProfile
      }
      category {
        ...MinimalGameCategory
      }
      approvalDate
      priorityPosition
      createdAt
      viewsCounter
      dealsCounter
      feeMultiplier
      isAutomated
    }
  }
}

fragment RegularUserFragment on UserFragment {
  id
  username
  role
  avatarURL
  isOnline
  isBlocked
  rating
  testimonialCounter
  createdAt
  supportChatId
  systemChatId
}

fragment PartialFile on File {
  id
  url
}

fragment RegularGameProfile on GameProfile {
  id
  name
  type
  slug
  logo {
    ...PartialFile
  }
}

fragment MinimalGameCategory on GameCategory {
  id
  slug
  name
}
""",