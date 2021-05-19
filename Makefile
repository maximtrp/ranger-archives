RANGER_DIR=$(if $(XDG_CONFIG_HOME),$(XDG_CONFIG_HOME),$(HOME)/.config)/ranger
PLUGIN_DIR=$(RANGER_DIR)/plugins
RM ?= $(shell which rm)

install:
	mkdir -p $(PLUGIN_DIR)
	cp -r ranger-archives $(PLUGIN_DIR)

uninstall:
	$(RM) -rf $(PLUGIN_DIR)/ranger-archives
