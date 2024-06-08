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
            amsmath
            dirtree
            ellipsis
            enumitem
            etoc
            etoolbox
            fontspec
            footmisc
            setspace
            titlesec
            ;
        };
        py = pkgs.python311.withPackages (ps: with ps; [
          jinja2
        ]);
      in
      {
        devShell = pkgs.mkShell {
          buildInputs = [
            (pkgs.buildEnv {
              name = "studies-env";
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
          shellHook = ''
            find-up () {
              path=$(pwd)
              while [[ "$path" != "" && ! -e "$path/$1" ]]; do
                path=''${path%/*}
              done
              echo "$path"
            }

            export PROJECT_ROOT="$(find-up flake.nix)"
          '';
        };
      }
    );
}
