<template :class="{ dark: isDarkMode }">
  <div class="flex flex-col chat-window">
    <!-- toolbar -->
    <div class="overflow-hidden w-full h-full relative flex z-0">
      <!-- sidebar -->
      <SideBar
        :conversations="conversations"
        @add-conversation="onAddConversation"
        :selectedConversationId="parseInt(conversation_id)"
        @select-conversation="onSelectConversation"
        @rename-conversation="onRenameConversation"
        @delete-conversation="onDeleteConversation"></SideBar>
      <!-- main body -->
      <div class="relative flex h-full max-w-full flex-1 overflow-hidden">
        <div class="flex-grow overflow-y-auto" ref="messageContainer">
          <div class="mx-auto max-w-2xl mt-5">
            <chat-bubble v-for="(message, index) in messages" :key="index" :message="message" @messageRendered="onMessageRendered"></chat-bubble>
          </div>
        </div>
        <div class="absolute bottom-0 left-0 w-full border-t md:border-t-0 md:border-transparent md:bg-vert-light-gradient bg-white pt-4">
          <form @submit.prevent="sendMessage" class="px-4 py-2 w-3/4 mx-auto">
            <div class="flex items-center">
              <input
                ref="messageInput"
                v-model="messageInput"
                type="text"
                class="form-input flex-1 h-10 rounded-md border border-gray-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-400 focus:ring-white"
                placeholder="Type your message..." />
              <button
                type="submit"
                class="send-button h-10 ml-2 px-3 py-2 rounded-md text-sm font-medium text-white bg-blue-700 hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-800 focus:ring-white">
                <img src="../assets/send-message.svg" alt="Send" />
              </button>
              <file-upload
                extensions="txt"
                accept="text/plain"
                class="flex-shrink-0 h-10 ml-2 px-3 py-2 rounded-md text-sm font-medium text-white bg-gray-500 hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-gray-800 focus:ring-white"
                :multiple="false"
                :drop="false"
                :drop-directory="false"
                v-model="files"
                @input-file="onInputFile"
                aria-label="Upload a Text Document (.txt)"
                ref="upload">
                📁
              </file-upload>
            </div>
            <div class="flex items-center mt-2">
              <div class="upload">
                <ul v-if="files.length">
                  <li v-for="file in files" :key="file.id">
                    <span>{{ file.name }}</span>
                    <span v-if="file.error">{{ file.error }}</span>
                    <span v-else-if="file.success">success</span>
                    <span v-else-if="file.active">active</span>
                    <span v-else></span>
                  </li>
                </ul>
              </div>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
  import SideBar from './SideBar.vue';
  import ChatBubble from './ChatBubble.vue';
  import InternalService from '../services/internal';
  import FileUpload from 'vue-upload-component';
  import eventBus from '../services/eventBus';

  export default {
    components: {
      SideBar,
      ChatBubble,
      FileUpload,
    },
    data() {
      return {
        username: '',
        avatarUrl: localStorage.getItem('avatarUrl') || new URL('../assets/user_icon.png', import.meta.url).href,
        messages: [],
        conversations: [],
        files: [],
        messageInput: '',
        isDarkMode: localStorage.getItem('isDarkMode', 'false') === 'true',
      };
    },
    async created() {
      await this.onSetup();
    },
    mounted() {
      this.$refs.messageInput.focus();

      eventBus.$on('update-profile', this.updateProfile);
      eventBus.$on('clear-messages', this.clearMessages);
    },
    methods: {
      async onSetup() {
        this.conversation_id = localStorage.getItem('conversation_id');

        try {
          // Get or create conversation
          this.conversation = await InternalService.getConversation(this.conversation_id);
        } catch (e) {
          this.conversation_id = null;
          localStorage.removeItem('conversation_id');
        }

        // if this.conversation_id is null get the id from the newly created conversation
        if (!this.conversation_id) {
          this.conversation_id = this.conversation.id;
          localStorage.setItem('conversation_id', this.conversation_id);
        }

        this.messages = this.conversation.messages || [];
        this.username = localStorage.getItem('username') ? localStorage.getItem('username') : 'Anonymous';
        this.conversations = await InternalService.getConversations();
      },

      updateProfile(data) {
        this.username = data['username'];
        this.avatarUrl = data['avatarUrl'];

        // refresh the conversation messages to include new avatar
        this.onSelectConversation(this.conversation_id);
      },
      async clearMessages() {
        this.messages = [];
        await this.onSetup();
      },
      async sendMessage() {
        if (!this.messageInput || this.messageInput.length === 0) {
          return;
        }

        const userMessage = {
          created_at: Date.now(),
          text: this.messageInput,
          is_user: true,
          conversation_id: this.conversation_id,
        };

        this.messageInput = '';

        const userMessageResponse = await InternalService.sendMessage(this.conversation_id, userMessage);
        userMessage.id = userMessageResponse.id;

        this.messages.push(userMessage);

        // Show the loading message
        const loadingMessage = {
          created_at: Date.now(),
          text: '',
          is_user: false,
          isLoading: true,
          rating: 0,
          conversation_id: this.conversation_id,
        };

        this.messages.push(loadingMessage);

        const aiMessageText = await InternalService.queryLLM(this.conversation_id, userMessage.text);
        const aiMessage = {
          created_at: Date.now(),
          text: aiMessageText,
          is_user: false,
          conversation_id: this.conversation_id,
          rating: 0,
        };

        const aiMessageResponse = await InternalService.sendMessage(this.conversation_id, aiMessage);
        aiMessage.id = aiMessageResponse.id;

        // Remove the loading message
        this.messages = this.messages.filter((message) => !message.isLoading);
        this.messages.push(aiMessage);
      },
      onMessageRendered() {
        this.$refs.messageContainer.scrollTo(0, this.$refs.messageContainer.scrollHeight);
      },
      async onInputFile(newFile) {
        if (!newFile) return;

        // implement file upload
        const response = await InternalService.uploadFile(this.conversation_id, newFile);

        const message = {
          created_at: Date.now(),
          text: `<span style="color: brown; font-weight: bold;">${response.text}</span>`,
          is_user: false,
          conversation_id: this.conversation_id,
        };

        const messageResponse = await InternalService.sendMessage(this.conversation_id, message);

        this.messages.push(messageResponse);
        this.files = [];
      },
      async onAddConversation() {
        const conversation = await InternalService.createConversation();
        this.conversation_id = conversation.id;
        localStorage.setItem('conversation_id', conversation.id);
        this.messages = [];
        this.conversations = await InternalService.getConversations();
      },
      async onSelectConversation(conversation_id) {
        this.conversation_id = conversation_id;
        localStorage.setItem('conversation_id', conversation_id);
        this.conversation = await InternalService.getConversation(conversation_id);
        this.messages = this.conversation.messages || [];
      },
      async onRenameConversation(conversation_id, newTitle) {
        await InternalService.renameConversation(conversation_id, newTitle);
      },
      async onDeleteConversation(conversation_id) {
        await InternalService.deleteConversation(conversation_id);
        this.conversation_id = null;
        localStorage.removeItem('conversation_id');

        this.conversations = await InternalService.getConversations();

        if (this.conversations.length === 0) {
          await this.onSetup();
        } else {
          this.conversation_id = this.conversations[0].id;
          this.conversation = await InternalService.getConversation(this.conversation_id);
          localStorage.setItem('conversation_id', this.conversation_id);
          this.messages = this.conversation.messages || [];
        }
      },
      logout() {
        localStorage.removeItem('user');
        this.$router.push('/login');
      },
    },
  };
</script>

<style scoped>
  .chat-window {
    height: calc(100% - 64px);
  }
  .overflow-y-auto {
    overflow-y: scroll; /* add a scrollbar when the content overflows */
    height: 80%;
  }

  .send-button {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 5px 10px;
    background-color: #007bff;
    color: #fff;
    border: none;
    border-radius: 4px;
    cursor: pointer;
  }

  .send-button img {
    width: 20px;
    height: 20px;
  }

  .send-button:hover {
    background-color: #0056b3;
  }
</style>
