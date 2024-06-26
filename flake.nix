{
  description = "sunsetglow";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        tex = pkgs.texlive.combine {
          inherit (pkgs.texlive) scheme-small
            latexmk
            amsmath
            dirtree
            ellipsis
            enumitem
            etoc
            etoolbox
            fontspec
            footmisc
            listings
            setspace
            titlesec
            ;
        };
        py = pkgs.python311.withPackages (ps: with ps; [
          jinja2
          pytz
        ]);
        shellHook = ''
          find-up () {
            path=$(pwd)
            while [[ "$path" != "" && ! -e "$path/$1" ]]; do
              path=''${path%/*}
            done
            echo "$path"
          }
          export PROJECT_ROOT="$(find-up flake.nix)"
          export TEXINPUTS=":$PROJECT_ROOT/src/posts/tex:"
        '';
      in
      {
        packages = {
          # For running during deployments.
          levant = pkgs.levant;
        };
        devShells.default = pkgs.mkShell {
          inherit shellHook;
          buildInputs = [
            (pkgs.buildEnv {
              name = "sg-dev";
              paths = with pkgs; [
                bashInteractive
                coreutils
                moreutils
                findutils
                inotify-tools
                curl
                pandoc
                py
                tex
              ];
            })
          ];
        };
      }
    );
}
