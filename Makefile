build:
	./scripts/build.py

serve:
	./scripts/serve.py

watch:
	make build
	echo "Started watcher..."
	while true; do \
		inotifywait -qr -e modify -e create -e delete -e move --include 'src/.*$$' --include 'scripts/.*$$' .; \
		make build; \
	done

.PHONY: build serve watch
