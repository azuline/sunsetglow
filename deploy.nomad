job "sunsetglow-site" {
  datacenters = ["frieren"]
  namespace   = "sunsetglow"
  type        = "service"

  group "sunsetglow-site" {
    count = 1

    network {
      mode = "bridge"
    }

    service {
      name = "sunsetglow-site"
      port = "80"
      connect {
        sidecar_service {}
      }
      check {
        expose   = true
        type     = "http"
        path     = "/health"
        interval = "10s"
        timeout  = "2s"
      }
    }

    task "sunsetglow-site" {
      driver = "docker"
      config {
        image = "nginx"
        volumes = [
          "local/dist:/www",
          "local/nginx.conf:/etc/nginx/conf.d/default.conf",
        ]
      }
      artifact {
        source      = "[[.artifact_source_url]]"
        destination = "local/dist"
      }
      template {
        data          = <<EOF
server {
  listen 80;
  listen [::]:80;
  root /www;
  index index.html;

  location /health {
    return 200 'ok';
  }
}
EOF
        destination   = "local/nginx.conf"
        change_mode   = "signal"
        change_signal = "SIGHUP"
      }
    }
  }

  update {
    max_parallel      = 1
    health_check      = "checks"
    min_healthy_time  = "10s"
    healthy_deadline  = "1m"
    progress_deadline = "10m"
    auto_revert       = true
    auto_promote      = true
    canary            = 1
  }
}

