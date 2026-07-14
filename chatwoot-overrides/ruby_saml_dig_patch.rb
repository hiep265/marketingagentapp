# Patch ruby-saml 1.18+ Attributes to add #dig
# Chatwoot's SwitchLocale concern calls #dig on OmniAuth auth_hash
# which may contain RubySaml::Attributes objects that lack #dig.
if defined?(OneLogin::RubySaml::Attributes)
  unless OneLogin::RubySaml::Attributes.method_defined?(:dig)
    OneLogin::RubySaml::Attributes.class_eval do
      def dig(key, *rest)
        val = self[key]
        if rest.empty? || val.nil?
          val
        elsif val.respond_to?(:dig)
          val.dig(*rest)
        end
      end
    end
  end
end
