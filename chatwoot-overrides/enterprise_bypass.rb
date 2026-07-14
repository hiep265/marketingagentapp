# frozen_string_literal: true

Rails.application.config.to_prepare do
  # 1. Patch ChatwootApp
  if defined?(ChatwootApp)
    ChatwootApp.module_eval do
      class << self
        def enterprise?
          true
        end

        def chatwoot_cloud?
          false
        end

        def self_hosted_enterprise?
          true
        end
      end
    end
  end

  # 2. Patch ChatwootHub
  if defined?(ChatwootHub)
    ChatwootHub.class_eval do
      class << self
        def pricing_plan
          'enterprise'
        end

        def pricing_plan_quantity
          100_000
        end
      end
    end
  end

  # 3. Patch Featurable (Account features)
  if defined?(Featurable)
    Featurable.module_eval do
      def feature_enabled?(name)
        if ChatwootApp.enterprise?
          # Try to find in standard features
          feature = FEATURE_LIST.find { |f| f['name'] == name.to_s } if defined?(FEATURE_LIST)
          return true if feature&.dig('premium')

          # Try to find in enterprise premium features
          @premium_features_yml ||= YAML.safe_load(Rails.root.join('enterprise/config/premium_features.yml').read).freeze rescue []
          return true if @premium_features_yml.include?(name.to_s)
        end

        send("feature_#{name}?")
      end
    end
  end

  # 4. Patch PlanUsageAndLimits on Account
  if defined?(Enterprise::Account::PlanUsageAndLimits)
    Enterprise::Account::PlanUsageAndLimits.module_eval do
      def usage_limits
        {
          agents: ChatwootApp.max_limit,
          inboxes: ChatwootApp.max_limit,
          captain: {
            documents: {
              total_count: ChatwootApp.max_limit,
              current_available: ChatwootApp.max_limit,
              consumed: 0
            },
            responses: {
              total_count: ChatwootApp.max_limit,
              current_available: ChatwootApp.max_limit,
              consumed: 0
            }
          }
        }
      end

      def captain_monthly_limit
        {
          documents: ChatwootApp.max_limit,
          responses: ChatwootApp.max_limit
        }.with_indifferent_access
      end

      def agent_limits
        ChatwootApp.max_limit
      end

      def get_limits(limit_name)
        ChatwootApp.max_limit
      end
    end
  end

  # 5. Patch GlobalConfig (pricing plan name and quantity)
  if defined?(GlobalConfig)
    GlobalConfig.class_eval do
      class << self
        unless method_defined?(:load_from_cache_without_bypass)
          alias_method :load_from_cache_without_bypass, :load_from_cache
          
          def load_from_cache(config_key)
            if config_key == 'INSTALLATION_PRICING_PLAN'
              'enterprise'
            elsif config_key == 'INSTALLATION_PRICING_PLAN_QUANTITY'
              100_000
            else
              load_from_cache_without_bypass(config_key)
            end
          end
        end
      end
    end
  end
end
