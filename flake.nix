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
        devShells = {
          build = pkgs.mkShell {
            inherit shellHook;
            buildInputs = [
              (pkgs.buildEnv {
                name = "sg-build";
                paths = with pkgs; [
                  coreutils
                  moreutils
                  findutils
                  curl
                  pandoc
                  py
                  tex
                ];
              })
            ];
          };
          deploy = pkgs.mkShell {
            inherit shellHook;
            buildInputs = [
              (pkgs.buildEnv {
                name = "sg-deploy";
                paths = with pkgs; [
                  coreutils
                  moreutils
                  findutils
                  levant
                ];
              })
            ];
          };
          default = pkgs.mkShell {
            inherit shellHook;
            buildInputs = [
              (pkgs.buildEnv {
                name = "sg-dev";
                paths = with pkgs; [
                  coreutils
                  moreutils
                  findutils
                  inotify-tools
                  pandoc
                  py
                  tex
                ];
              })
            ];
          };
        };
      }
    );
}
